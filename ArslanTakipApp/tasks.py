from celery import shared_task
from .models import Hareket
from .email_utils import check_new_emails
from .uretim_raporu import check_new_rapor


@shared_task
def start_email_listener():
    check_new_emails()

@shared_task
def start_rapor_listener():
    check_new_rapor()

