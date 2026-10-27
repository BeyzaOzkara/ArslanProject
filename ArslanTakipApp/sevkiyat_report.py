"""Sevkiyat tamam maili için aylık sevkiyat raporu."""

import os
from datetime import datetime
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup
from django.db.models import Sum
from django.template.loader import render_to_string

from .models import Firma, SevkiyatFaturaListesi, UrunCikisi


# SEVKIYAT_SENDER = 'serkankutluca@arslanaluminyum.com'

SEVKIYAT_SENDER = os.environ.get('SEVKIYAT_SENDER', 'yazilim@arslanaluminyum.com').strip().lower()

def normalize_text(value):
    return ' '.join((value or '').replace('İ', 'i').casefold().split())


def is_sevkiyat_completed(message):
    sender = getattr(getattr(message, 'sender', None), 'email_address', '')
    if normalize_text(sender) != SEVKIYAT_SENDER:
        return False
    if normalize_text(message.subject) != 'sevkiyat':
        return False
    text = message.text_body
    if not text:
        text = BeautifulSoup(str(message.body or ''), 'html.parser').get_text(' ', strip=True)
    return normalize_text(text) == 'sevkiyat tamam'


def get_monthly_shipped_kg(now=None):
    now = now or datetime.now(ZoneInfo('Europe/Istanbul'))
    if now.tzinfo is not None:
        now = now.astimezone(ZoneInfo('Europe/Istanbul')).replace(tzinfo=None)
    # SQL Server bağlantısında ve projede USE_TZ=False kullanılıyor.
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end = start.replace(year=start.year + (start.month == 12), month=start.month % 12 + 1)
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
    return start, total


def send_sevkiyat_report():
    from .email_utils import send_email

    recipients = [address.strip() for address in os.environ.get(
        'SEVKIYAT_REPORT_TO', 'yazilim@arslanaluminyum.com'
    ).split(',') if address.strip()]
    if not recipients:
        raise ValueError('Sevkiyat raporu için SEVKIYAT_REPORT_TO tanımlanmalı.')
    start, total = get_monthly_shipped_kg()
    body = render_to_string('mail/sevkiyat_report.html', {
        'period': start.strftime('%m/%Y'),
        'total_kg': total,
    })
    if not send_email(recipients, [], f'Sevkiyat Raporu - {start:%m/%Y}', body):
        raise RuntimeError('Sevkiyat raporu gönderilemedi.')
