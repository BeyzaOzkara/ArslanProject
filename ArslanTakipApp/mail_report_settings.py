"""Admin'de yönetilen mail raporu ayarları; gönderim sırasında önbelleksiz okunur."""
import re

from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.validators import validate_email


def parse_email_addresses(value):
    addresses = []
    invalid = []
    for token in re.split(r'[\s,;]+', value or ''):
        address = token.strip().lower()
        if not address:
            continue
        try:
            validate_email(address)
        except ValidationError:
            invalid.append(address)
            continue
        if address not in addresses:
            addresses.append(address)
    if invalid:
        raise ValidationError('Geçersiz e-posta adresleri: %(addresses)s',
                              params={'addresses': ', '.join(invalid)})
    return addresses


def get_sevkiyat_settings():
    from .models import MailReportSettings

    try:
        return MailReportSettings.objects.using('default').get(code='sevkiyat')
    except MailReportSettings.DoesNotExist as exc:
        # Silinmiş ayarlarda eski sabit listelere dönüp yanlış kişilere gönderme.
        raise ImproperlyConfigured(
            'Sevkiyat mail ayarı bulunamadı. MailReportSettings migrationını ve admin kaydını kontrol edin.'
        ) from exc
