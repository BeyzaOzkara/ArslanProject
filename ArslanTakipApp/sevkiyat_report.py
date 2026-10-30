"""Sevkiyat tamam maili için aylık sevkiyat raporu."""

import logging
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup
from django.core.exceptions import ImproperlyConfigured
from django.db.models import Sum
from django.template.loader import render_to_string

from .mail_report_settings import get_sevkiyat_settings
from .models import Firma, SevkiyatFaturaListesi, SevkiyatRaporu, UrunCikisi

logger = logging.getLogger(__name__)


def normalize_text(value):
    return ' '.join((value or '').replace('İ', 'i').casefold().split())


def is_sevkiyat_completed(message):
    if normalize_text(message.subject) != 'sevkiyat':
        logger.info('SEVKIYAT SKIP subject=%r expected=sevkiyat', message.subject)
        return False
    report_settings = get_sevkiyat_settings()
    if not report_settings.is_active:
        logger.info('SEVKIYAT SKIP report disabled in admin')
        return False
    sender = getattr(getattr(message, 'sender', None), 'email_address', '')
    allowed_senders = report_settings.addresses('sender_addresses')
    if normalize_text(sender) not in allowed_senders:
        logger.info('SEVKIYAT SKIP sender=%s expected=%s', sender, allowed_senders)
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
    rows = get_shipment_groups(start, end, by_sales_position=True)
    logger.info('SEVKIYAT DETAIL date=%s rows=%s', day, len(rows))
    return rows


def get_shipment_queryset(start, end):
    # SQL'deki != NULL satırlarını da dışlar; exclude tek başına aynı değildir.
    shipment_ids = SevkiyatRaporu.objects.using('dies').filter(
        KartTuru__isnull=False,
    ).exclude(KartTuru='Fason').order_by().values('Kimlik').distinct()
    return UrunCikisi.objects.using('dies').filter(
        Tarih__gte=start, Tarih__lt=end,
        SevkEdildi='EVET', Kimlik__in=shipment_ids,
    )


def normalize_company_name(name):
    normalized = normalize_text(name)
    if 'alumeco' in normalized:
        return 'Alumeco'
    if 'perpolio' in normalized or 'alufortis' in normalized:
        return 'PERPOLIO/ALUFORTİS'
    return name


def get_shipment_groups(start, end, by_sales_position=False):
    # Eski mssql-django sürümlerinde CASE ifadesiyle GROUP BY hatalı SQL
    # üretebiliyor. SQL'de gerçek kolonları grupla; normalize adları sonra birleştir.
    fields = ['FirmaAdi', 'SatisPozisyon'] if by_sales_position else ['FirmaAdi']
    raw_rows = get_shipment_queryset(start, end).order_by().values(*fields).annotate(
        TOPLAM=Sum('ToplamKg'),
    )
    groups = {}
    for row in raw_rows:
        company = normalize_company_name(row['FirmaAdi'])
        key = (company, row['SatisPozisyon']) if by_sales_position else (company,)
        if key not in groups:
            groups[key] = {'Firma': company, 'TOPLAM': None}
            if by_sales_position:
                groups[key]['SatisPozisyon'] = row['SatisPozisyon']
        if row['TOPLAM'] is not None:
            groups[key]['TOPLAM'] = (groups[key]['TOPLAM'] or 0) + row['TOPLAM']
    rows = sorted(groups.values(), key=lambda row: row['Firma'] or '')
    # SQL Server DESC sıralamasındaki gibi NULL toplamlar en sonda.
    return sorted(rows, key=lambda row: (row['TOPLAM'] is not None, row['TOPLAM'] or 0), reverse=True)


def get_monthly_top_shipment_firms(now=None):
    now = now or datetime.now(ZoneInfo('Europe/Istanbul'))
    if now.tzinfo is not None:
        now = now.astimezone(ZoneInfo('Europe/Istanbul')).replace(tzinfo=None)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end = start.replace(year=start.year + (start.month == 12), month=start.month % 12 + 1)
    # Bir firmanın tüm satış pozisyonlarını tek toplamda birleştir.
    rows = get_shipment_groups(start, end)[:5]
    logger.info('SEVKIYAT MONTHLY TOP5 start=%s end_exclusive=%s rows=%s', start, end, len(rows))
    return rows


def send_sevkiyat_report(shipment_datetime=None, sender_email=None):
    from .email_utils import send_email
    from .sevkiyat_pdf import build_sevkiyat_pdf

    report_settings = get_sevkiyat_settings()
    if not report_settings.is_active:
        logger.info('SEVKIYAT REPORT SKIP report disabled in admin')
        return False
    sender = normalize_text(sender_email)
    if sender_email and sender not in report_settings.addresses('sender_addresses'):
        logger.info('SEVKIYAT REPORT SKIP sender no longer allowed: %s', sender)
        return False
    if sender and sender in report_settings.addresses('test_sender_addresses'):
        recipients = [sender]
        cc_recipients = [sender]
    else:
        recipients = report_settings.addresses('to_addresses')
        cc_recipients = report_settings.addresses('cc_addresses')
    if not recipients:
        raise ImproperlyConfigured('Sevkiyat raporunun alıcı listesi boş. Admin panelindeki ayarı kontrol edin.')
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
