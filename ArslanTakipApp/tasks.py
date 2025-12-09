from celery import shared_task
from .email_utils import check_new_emails
from .uretim_raporu import check_new_rapor
from .die_update import check_new_dies, check_die_deletes
from .reports import send_report_email_for_all
from .utilities.test_report import send_daily_test_report_for_all, send_new_dies_without_orders_report
import logging
from django.utils import timezone
from django.core.cache import cache

logger = logging.getLogger(__name__)

# @shared_task # bu yok
# def start_email_listener():
#     check_new_emails()

@shared_task # 
def start_rapor_listener():
    check_new_rapor()

@shared_task #
def start_die_listener():
    """
    NOT: Artık sonsuz döngü DEĞİL.
    - Tek seferde yeni kalıpları ve silinenleri kontrol eder.
    - Aynı anda sadece 1 instance çalışsın diye basit bir lock kullanır.
    """
    lock_id = "start_die_listener_lock"
    # 4 dakika süren bir lock (gereğine göre değiştir)
    if not cache.add(lock_id, "true", 60 * 12):
        # Başka bir instance çalışıyor, bu task direkt çıksın
        return

    try:
        check_new_dies()
        check_die_deletes()
    finally:
        cache.delete(lock_id)

@shared_task # bu yok
def start_report__for_everyone_listener():
    send_report_email_for_all()

@shared_task # bu yok
def start_report_listener_for_():
    send_report_email_for_all()

@shared_task(ignore_result=True)
def start_test_report_listener():
    logger.info(">>> start_test_report_listener tetiklendi: %s", timezone.now())
    try:
        send_daily_test_report_for_all()
        logger.info(">>> daily_test başarıyla bitti")
    except Exception as e:
        logger.exception("!!! daily_test hata verdi: %s", e)
        raise

@shared_task
def start_new_dies_without_orders_report_listener():
    try:
        send_new_dies_without_orders_report()
        logger.info(">>> new_dies başarıyla bitti")
    except Exception as e:
        logger.exception("!!! new_dies hata verdi: %s", e)
        raise