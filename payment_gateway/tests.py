from decimal import Decimal
from unittest.mock import patch

from django.test import SimpleTestCase

from .services import PaystackService


class PaystackServiceCurrencyTests(SimpleTestCase):
    @patch('payment_gateway.services.requests.post')
    def test_initialize_payment_uses_usd_currency(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'status': True,
            'data': {'authorization_url': 'https://paystack.test/checkout'},
            'message': 'ok',
        }

        service = PaystackService()
        service.initialize_payment(
            email='payer@example.com',
            amount=Decimal('75.00'),
            reference='PAY-USD-1',
            metadata={'job_id': '123'},
        )

        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['currency'], 'USD')

from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from orders.models import Job
from payment_gateway.models import Payment, PaymentStatus
from user_module.models import User, Role


class InitializePaymentViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user, _ = User.objects.create_client(email="client@example.com", activate=True)
        self.freelancer, _ = User.objects.create_freelancer(
            email="freelancer@example.com",
            password="StrongPass123!",
            activate=True,
        )
        self.job = Job.objects.create(
            title="Test job",
            description="Payment initialization test",
            client=self.user,
            freelancer=self.freelancer,
            price=Decimal("50.00"),
            total_amount=Decimal("50.00"),
            delivery_time_days=3,
            allowed_reviews=1,
            status="PROVISIONAL",
        )

    @patch("payment_gateway.views.PaystackService.initialize_payment")
    def test_initialize_payment_returns_400_for_upstream_rejection(self, mock_initialize):
        mock_initialize.return_value = {
            "success": False,
            "message": "Currency not supported",
            "data": {"status": False, "message": "Currency not supported"},
        }

        response = self.client.post(
            "/api/payments/initialize/",
            {"job_id": str(self.job.id), "email": self.user.email},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "Payment initialization failed")
        self.assertIn("Currency not supported", response.data["detail"])

        payment = Payment.objects.get(job=self.job)
        self.assertEqual(payment.status, PaymentStatus.FAILED)

    @patch("payment_gateway.views.PaystackService.initialize_payment")
    def test_initialize_payment_returns_502_for_network_failure(self, mock_initialize):
        mock_initialize.return_value = {
            "success": False,
            "message": "Network error: timed out",
            "data": {},
        }

        response = self.client.post(
            "/api/payments/initialize/",
            {"job_id": str(self.job.id), "email": self.user.email},
            format="json",
        )

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.data["error"], "Payment initialization failed")
        self.assertIn("Network error", response.data["detail"])

    @patch('payment_gateway.services.requests.post')
    def test_initialize_payment_does_not_fall_back_to_kes_on_usd_forbidden(self, mock_post):
        usd_resp = type('Resp', (), {})()
        usd_resp.status_code = 403
        usd_resp.json = lambda: {'status': False, 'message': 'Currency not supported'}

        mock_post.return_value = usd_resp

        service = PaystackService()
        result = service.initialize_payment(
            email='payer@example.com',
            amount=Decimal('75.00'),
            reference='PAY-FALLBACK-1',
            metadata={'job_id': '123'},
        )

        self.assertFalse(result.get('success'))
        self.assertEqual(mock_post.call_count, 1)
        self.assertEqual(mock_post.call_args.kwargs['json']['currency'], 'USD')

    @patch('orders.workflow.send_mail')
    def test_payment_success_marks_job_in_progress_and_sets_deadline(self, mock_send_mail):
        payment = Payment.objects.create(
            job=self.job,
            user=self.user,
            amount=Decimal("50.00"),
            currency="USD",
            reference="PAY-SUCCESS-1",
            status=PaymentStatus.PENDING,
        )

        before = timezone.now()
        payment.mark_as_successful({"status": "success"})

        self.job.refresh_from_db()
        payment.refresh_from_db()

        self.assertEqual(payment.status, PaymentStatus.SUCCESS)
        self.assertEqual(self.job.status, "IN_PROGRESS")
        self.assertEqual(self.job.paystack_status, "success")
        self.assertIsNotNone(self.job.work_started_at)
        self.assertIsNotNone(self.job.delivery_due_at)
        self.assertGreaterEqual(self.job.work_started_at, before)
        self.assertGreater(self.job.delivery_due_at, self.job.work_started_at)
        mock_send_mail.assert_called_once()