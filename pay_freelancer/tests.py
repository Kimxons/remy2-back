import json
from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase

from pay_freelancer.api_utils import create_transfer_recipient
from pay_freelancer.models import Payout
from user_module.models import User


class PayoutCurrencyTests(TestCase):
	def setUp(self):
		self.client_user, _ = User.objects.create_client(
			email='client@example.com',
			activate=True,
		)
		self.freelancer, _ = User.objects.create_freelancer(
			email='freelancer@example.com',
			password='StrongPass123!',
			activate=True,
		)
		from orders.models import Job

		self.job = Job.objects.create(
			title='USD payout job',
			description='Validation fixture for payout currency tests',
			client=self.client_user,
			freelancer=self.freelancer,
			price=Decimal('25.50'),
			total_amount=Decimal('25.50'),
			delivery_time_days=3,
		)

	def test_payout_uses_usd_amount_without_conversion(self):
		payout = Payout.objects.create(
			job=self.job,
			freelancer=self.freelancer,
			usd_amount=Decimal('25.50'),
		)

		self.assertEqual(payout.currency, 'USD')
		self.assertEqual(payout.applied_rate, Decimal('1.00'))
		self.assertEqual(payout.payout_amount, Decimal('25.50'))

	def test_payout_rejects_amount_below_usd_minimum(self):
		payout = Payout(
			job=self.job,
			freelancer=self.freelancer,
			usd_amount=Decimal('5.00'),
		)

		with self.assertRaises(ValidationError) as error:
			payout.full_clean()

		self.assertIn('Minimum is $10.00.', str(error.exception))


class PaystackRecipientCurrencyTests(TestCase):
	@patch('pay_freelancer.api_utils.requests.post')
	def test_create_transfer_recipient_uses_usd_currency(self, mock_post):
		response = mock_post.return_value
		response.raise_for_status.return_value = None
		response.json.return_value = {'status': True, 'data': {'recipient_code': 'RCP_test'}}

		create_transfer_recipient('Freelancer', '1234567890', '001')

		payload = json.loads(mock_post.call_args.kwargs['data'])
		self.assertEqual(payload['currency'], 'USD')
