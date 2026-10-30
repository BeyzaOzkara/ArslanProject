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


def get_report_settings(code):
    from .models import MailReportSettings

    try:
        return MailReportSettings.objects.using('default').get(code=code)
    except MailReportSettings.DoesNotExist as exc:
        # Silinmiş ayarlarda eski sabit listelere dönüp yanlış kişilere gönderme.
        raise ImproperlyConfigured(
            f'{code} mail ayarı bulunamadı. MailReportSettings migrationını ve admin kaydını kontrol edin.'
        ) from exc


def get_sevkiyat_settings():
    return get_report_settings('sevkiyat')


def get_scheduled_report_recipients(code):
    """Her çalışmada güncel dağıtımı oku; pasif raporlarda sorgulara bile başlama."""
    import logging

    config = get_report_settings(code)
    if not config.is_active:
        logging.getLogger(__name__).info('SCHEDULED REPORT SKIP code=%s disabled in admin', code)
        return None
    recipients = config.addresses('to_addresses')
    cc = config.addresses('cc_addresses')
    if not recipients:
        raise ImproperlyConfigured(f'{code} raporunun alıcı listesi boş. Admin ayarını kontrol edin.')
    return recipients, cc


def get_event_report_recipients(code, route_key, actor_email='', representative_emails=(), report_settings=None):
    """Ortak liste + pres listesi + etkinleştirilmiş dinamik alıcılar."""
    import logging

    if code not in ('die_transfer', 'die_test'):
        raise ValueError('Bu rapor pres dağıtımı kullanmıyor.')
    config = report_settings if report_settings is not None else get_report_settings(code)
    if not config.is_active:
        return None
    route_key = (route_key or '').strip()
    route = config.routes.using('default').filter(route_key=route_key).first()
    if route and not route.is_active:
        logging.getLogger(__name__).info('EVENT REPORT SKIP code=%s route=%s disabled', code, route_key)
        return None
    if route is None and code == 'die_test':
        raise ImproperlyConfigured(f'{route_key!r} presi için test mail dağıtımı bulunamadı. Admin ayarını kontrol edin.')
    to = config.addresses('to_addresses')
    cc = config.addresses('cc_addresses')
    if route:
        to += route.addresses('to_addresses')
        cc += route.addresses('cc_addresses')
    if config.include_actor and actor_email:
        to += parse_email_addresses(actor_email)
    if config.include_representative:
        for address in representative_emails:
            to += parse_email_addresses(address)
    to = list(dict.fromkeys(to))
    cc = list(dict.fromkeys(cc))
    if not to:
        raise ImproperlyConfigured(f'{code} / {route_key} için alıcı listesi boş. Admin ayarını kontrol edin.')
    return to, cc
