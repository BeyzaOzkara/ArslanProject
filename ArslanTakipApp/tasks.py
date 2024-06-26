from celery import shared_task
from .models import Hareket
from .email_utils import check_new_emails


@shared_task
def start_email_listener():
    check_new_emails()