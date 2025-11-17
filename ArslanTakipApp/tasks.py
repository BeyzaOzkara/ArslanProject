from celery import shared_task
from .email_utils import check_new_emails
from .uretim_raporu import check_new_rapor
from .die_update import check_new_dies, check_die_deletes
from .reports import send_report_email_for_all
from .utilities.test_report import send_daily_test_report_for_all, send_new_dies_without_orders_report
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)

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
    send_report_email_for_all()

@shared_task
def start_test_report_listener():
    logger.info(">>> start_test_report_listener tetiklendi: %s", timezone.now())
    # send_daily_test_report_for_all()
    # send_new_dies_without_orders_report()
    try:
        send_daily_test_report_for_all()
        logger.info(">>> daily_test başarıyla bitti")
    except Exception as e:
        logger.exception("!!! daily_test hata verdi: %s", e)
        raise
    try:
        send_new_dies_without_orders_report()
        logger.info(">>> new_dies başarıyla bitti")
    except Exception as e:
        logger.exception("!!! new_dies hata verdi: %s", e)
        raise