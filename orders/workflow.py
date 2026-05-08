from datetime import timedelta
import logging

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import JobStatus

logger = logging.getLogger(__name__)


def _send_freelancer_payment_started_email(job):
    freelancer = getattr(job, "freelancer", None)
    if not freelancer or not freelancer.email:
        return

    due_at = getattr(job, "delivery_due_at", None)
    due_line = (
        f"Delivery due: {timezone.localtime(due_at).strftime('%Y-%m-%d %H:%M %Z')}\n"
        if due_at else ""
    )

    send_mail(
        subject="A paid job is now in progress",
        message=(
            f"Hello {freelancer.username},\n\n"
            f'The job "{job.title}" has been paid for and is now in progress.\n'
            "Your delivery countdown has started.\n"
            f"{due_line}"
            "Please log in to review the order details and begin work.\n\n"
            "RemyInk Team"
        ),
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        recipient_list=[freelancer.email],
        fail_silently=False,
    )


def activate_job_after_payment(job, gateway_status="success"):
    now = timezone.now()
    previous_status = job.status
    update_fields = []

    if job.status != JobStatus.IN_PROGRESS:
        job.status = JobStatus.IN_PROGRESS
        update_fields.append("status")

    if job.paystack_status != gateway_status:
        job.paystack_status = gateway_status
        update_fields.append("paystack_status")

    if not getattr(job, "work_started_at", None):
        job.work_started_at = now
        update_fields.append("work_started_at")

    if not getattr(job, "delivery_due_at", None) and job.delivery_time_days:
        job.delivery_due_at = now + timedelta(days=int(job.delivery_time_days))
        update_fields.append("delivery_due_at")

    if update_fields:
        job.save(update_fields=[*update_fields, "updated_at"])

    if previous_status != JobStatus.IN_PROGRESS:
        try:
            _send_freelancer_payment_started_email(job)
        except Exception as exc:
            logger.warning(f"Failed to send freelancer payment email for job {job.id}: {exc}")

    return job