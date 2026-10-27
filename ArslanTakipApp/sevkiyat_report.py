"""Sevkiyat tamam maili için aylık sevkiyat raporu."""

import logging
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup
from django.db.models import Case, CharField, F, Q, Sum, Value, When
from django.template.loader import render_to_string

from .models import Firma, SevkiyatFaturaListesi, SevkiyatRaporu, UrunCikisi

logger = logging.getLogger(__name__)

SEVKIYAT_TEST_SENDER = 'yazilim@arslanaluminyum.com'
SEVKIYAT_SENDERS = (
    'serkankutluca@arslanaluminyum.com',
    'furkankaya@arslanaluminyum.com',
    SEVKIYAT_TEST_SENDER,
)
SEVKIYAT_REPORT_TO = [
    'burakduman@arslanaluminyum.com',
    'doganyilmaz@arslanaluminyum.com',
    'nilgunhaydar@arslanaluminyum.com',
    'paketleme2@arslanaluminyum.com',
    'paketleme@arslanaluminyum.com',
    'mekanikislem@arslanaluminyum.com',
    'ozkankavak@arslanaluminyum.com',
    'yuzeyislem@arslanaluminyum.com',
    'eloksal@arslanaluminyum.com',
    'ozgurcubukcu@arslanaluminyum.com',
    'kalitemuhendisi@arslanaluminyum.com',
    'kalitekontrol@arslanaluminyum.com',
    'akenanatagur@arslanaluminyum.com',
    'boyahane2@arslanaluminyum.com',
    'serkankutluca@arslanaluminyum.com',
    'furkankaya@arslanaluminyum.com',
    'hasanhuseyinkurut@arslanaluminyum.com',
    'mehmetsimsir@arslanaluminyum.com',
    'aysegularabaci@arslanaluminyum.com',
    'pres2@arslanaluminyum.com',
    'pres1@arslanaluminyum.com',
    '4.fabrikabakim@arslanaluminyum.com',
    'fatmadeniz@arslanaluminyum.com',
    'hasanpasa@arslanaluminyum.com',
    'cagataycevik@arslanaluminyum.com',
    'argemuhendisi2@arslanaluminyum.com',
    'export@arslanaluminyum.com',
    'huseyindogruoz@arslanaluminyum.com',
]
SEVKIYAT_REPORT_CC = [
    'ersoy@arslanaluminyum.com',
    'aosman@arslanaluminyum.com',
    'ufukizgi@arslanaluminyum.com',
    'pinararslan@arslanaluminyum.com',
    'serdarfurtuna@arslanaluminyum.com',
    'turkerozdener@arslanaluminyum.com',
    'haruncan@arslanaluminyum.com',
]

def normalize_text(value):
    return ' '.join((value or '').replace('İ', 'i').casefold().split())


def is_sevkiyat_completed(message):
    sender = getattr(getattr(message, 'sender', None), 'email_address', '')
    if normalize_text(sender) not in SEVKIYAT_SENDERS:
        logger.info('SEVKIYAT SKIP sender=%s expected=%s', sender, SEVKIYAT_SENDERS)
        return False
    if normalize_text(message.subject) != 'sevkiyat':
        logger.info('SEVKIYAT SKIP subject=%r expected=sevkiyat', message.subject)
        return False
    text = message.text_body
    if not text:
        text = BeautifulSoup(str(message.body or ''), 'html.parser').get_text(' ', strip=True)
    matches = normalize_text(text) == 'sevkiyat tamam'
    logger.info('SEVKIYAT %s body_matches=%s body_length=%s (imza/ek metin eslesmeyi engeller)',
                'MATCH' if matches else 'SKIP', matches, len(text or ''))
    return matches


def get_monthly_shipped_kg(now=None):
    now = now or datetime.now(ZoneInfo('Europe/Istanbul'))
    if now.tzinfo is not None:
        now = now.astimezone(ZoneInfo('Europe/Istanbul')).replace(tzinfo=None)
    # SQL Server bağlantısında ve projede USE_TZ=False kullanılıyor.
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end = start.replace(year=start.year + (start.month == 12), month=start.month % 12 + 1)
    return start, get_shipped_kg(start, end)


def get_daily_shipped_kg(now=None):
    now = now or datetime.now(ZoneInfo('Europe/Istanbul'))
    if now.tzinfo is not None:
        now = now.astimezone(ZoneInfo('Europe/Istanbul')).replace(tzinfo=None)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, get_shipped_kg(start, start + timedelta(days=1))


def get_shipped_kg(start, end):
    logger.info('SEVKIYAT QUERY database=dies start=%s end_exclusive=%s', start, end)
    shipment_ids = SevkiyatFaturaListesi.objects.using('dies').filter(
        Tarih__gte=start,
        Tarih__lt=end,
        KartTuru__in=['Siparis', 'Deneme', 'Devir', 'Stok', 'Fason Urt.', 'Iade'],
        SevkEdildi='EVET',
    ).order_by().values('Kimlik')
    total = UrunCikisi.objects.using('dies').filter(
        Kimlik__in=shipment_ids,
        FirmaKodu__in=Firma.objects.using('dies').order_by().values('FirmaKodu'),
    ).aggregate(total=Sum('ToplamKg', default=0.0))['total']
    logger.info('SEVKIYAT QUERY OK total_kg=%s', total)
    return total


def get_daily_shipment_breakdown(day):
    start = datetime.combine(day, time.min)
    end = start + timedelta(days=1)
    rows = list(get_normalized_shipments(start, end).values(
        'Firma', 'SatisPozisyon',
    ).annotate(TOPLAM=Sum('ToplamKg')).order_by('-TOPLAM'))
    logger.info('SEVKIYAT DETAIL date=%s rows=%s', day, len(rows))
    return rows


def get_normalized_shipments(start, end):
    # SQL'deki != NULL satırlarını da dışlar; exclude tek başına aynı değildir.
    shipment_ids = SevkiyatRaporu.objects.using('dies').filter(
        KartTuru__isnull=False,
    ).exclude(KartTuru='Fason').order_by().values('Kimlik').distinct()
    return UrunCikisi.objects.using('dies').filter(
        Tarih__gte=start, Tarih__lt=end,
        SevkEdildi='EVET', Kimlik__in=shipment_ids,
    ).annotate(Firma=Case(
        When(FirmaAdi__icontains='Alumeco', then=Value('Alumeco')),
        When(Q(FirmaAdi__icontains='PERPOLIO')
             | Q(FirmaAdi__icontains='ALUFORTİS')
             | Q(FirmaAdi__icontains='ALUFORTIS'), then=Value('PERPOLIO/ALUFORTİS')),
        default=F('FirmaAdi'), output_field=CharField(),
    ))


def get_monthly_top_shipment_firms(now=None):
    now = now or datetime.now(ZoneInfo('Europe/Istanbul'))
    if now.tzinfo is not None:
        now = now.astimezone(ZoneInfo('Europe/Istanbul')).replace(tzinfo=None)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end = start.replace(year=start.year + (start.month == 12), month=start.month % 12 + 1)
    # Bir firmanın tüm satış pozisyonlarını tek toplamda birleştir.
    rows = list(get_normalized_shipments(start, end).values('Firma').annotate(
        TOPLAM=Sum('ToplamKg'),
    ).order_by('-TOPLAM', 'Firma')[:5])
    logger.info('SEVKIYAT MONTHLY TOP5 start=%s end_exclusive=%s rows=%s', start, end, len(rows))
    return rows


def send_sevkiyat_report(shipment_datetime=None, sender_email=None):
    from .email_utils import send_email
    from .sevkiyat_pdf import build_sevkiyat_pdf

    if normalize_text(sender_email) == SEVKIYAT_TEST_SENDER:
        recipients = [SEVKIYAT_TEST_SENDER]
        cc_recipients = [SEVKIYAT_TEST_SENDER]
    else:
        recipients = list(SEVKIYAT_REPORT_TO)
        cc_recipients = list(SEVKIYAT_REPORT_CC)
    logger.info('SEVKIYAT REPORT START recipients=%s cc=%s', recipients, cc_recipients)
    now = datetime.now(ZoneInfo('Europe/Istanbul'))
    shipment_datetime = shipment_datetime or now
    if shipment_datetime.tzinfo is not None:
        shipment_datetime = shipment_datetime.astimezone(ZoneInfo('Europe/Istanbul'))
    logger.info('SEVKIYAT REPORT shipment_date=%s generated_at=%s', shipment_datetime.date(), now)
    start, total = get_monthly_shipped_kg(shipment_datetime)
    today, daily_total = get_daily_shipped_kg(shipment_datetime)
    detail_date = shipment_datetime.date()
    details = get_daily_shipment_breakdown(detail_date)
    top_firms = get_monthly_top_shipment_firms(shipment_datetime)
    # Yalnızca gösterim adlarını kısalt; gruplama ve toplamlar tam adlarla hesaplanır.
    details = [{**row, 'Firma': ' '.join((row['Firma'] or '').split()[:3]) or None}
               for row in details]
    top_firms = [{**row, 'Firma': ' '.join((row['Firma'] or '').split()[:3]) or None}
                 for row in top_firms]
    context = {
        'period': start.strftime('%m/%Y'),
        'total_kg': total,
        'today': today.strftime('%d.%m.%Y'),
        'daily_total_kg': daily_total,
        'detail_date': detail_date.strftime('%d.%m.%Y'),
        'details': details,
        'top_firms': top_firms,
        'report_date': now.strftime('%d.%m.%Y'),
        'report_time': now.strftime('%H:%M'),
        'detail_total_kg': sum((row['TOPLAM'] or 0) for row in details),
    }
    body = render_to_string('mail/sevkiyat_report.html', context)
    pdf = build_sevkiyat_pdf(context)
    filename = f'Sevkiyat_Raporu_{now:%Y-%m-%d_%H-%M}.pdf'
    logger.info('SEVKIYAT PDF READY name=%s bytes=%s', filename, len(pdf))
    if not send_email(recipients, cc_recipients, f'Sevkiyat Raporu - {now:%d/%m/%Y %H:%M}', body,
                      attachments=[(filename, pdf, 'application/pdf')]):
        raise RuntimeError('Sevkiyat raporu gönderilemedi.')
    logger.info('SEVKIYAT REPORT SENT recipients=%s', recipients)
