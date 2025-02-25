from celery import shared_task
from .email_utils import check_new_emails
from .uretim_raporu import check_new_rapor
from .die_update import check_new_dies, check_die_deletes
from .reports import send_report_email_for_all


@shared_task
def start_email_listener():
    check_new_emails()

@shared_task
def start_rapor_listener():
    check_new_rapor()

@shared_task
def start_die_listener():
    check_new_dies()
    check_die_deletes()

@shared_task
def start_report__for_everyone_listener():
    send_report_email_for_all()

@shared_task
def start_report_listener_for_():
    send_report_email_for_all
    
#her gün halka
#pazartesi, çarşamba, cuma pınar hanım