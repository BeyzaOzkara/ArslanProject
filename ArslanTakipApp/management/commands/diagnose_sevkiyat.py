"""Mail göndermeden ve işlenen mail kaydını değiştirmeden teşhis."""
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from django.core.management.base import BaseCommand, CommandError
from exchangelib import Account, Configuration, Credentials, DELEGATE

from ArslanTakipApp.models import LastProcessEmail
from ArslanTakipApp.sevkiyat_report import (
    SEVKIYAT_SENDERS, SEVKIYAT_REPORT_TO, SEVKIYAT_REPORT_CC, SEVKIYAT_TEST_SENDER,
    get_monthly_shipped_kg, get_daily_shipped_kg, get_daily_shipment_breakdown,
    get_monthly_top_shipment_firms, is_sevkiyat_completed,
)


class Command(BaseCommand):
    help = 'Sevkiyat mail akisini salt okunur kontrol eder; mail gondermez.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=10)
        parser.add_argument('--query', action='store_true', help='Kg sorgusunu da test et.')

    def handle(self, *args, **options):
        if options['limit'] < 1:
            raise CommandError('--limit en az 1 olmali.')
        mailbox = os.environ.get('AI_EMAIL_USER', 'ai@arslanaluminyum.com')
        password = os.environ.get('AI_EMAIL_PASSWORD', '')
        self.stdout.write(f'Izlenen gelen kutusu: {mailbox}')
        self.stdout.write('Beklenen gonderenler: ' + ', '.join(SEVKIYAT_SENDERS))
        self.stdout.write('Rapor alicilari: ' + ', '.join(SEVKIYAT_REPORT_TO))
        self.stdout.write('Rapor CC: ' + ', '.join(SEVKIYAT_REPORT_CC))
        self.stdout.write(f'Deneme gondereni {SEVKIYAT_TEST_SENDER}: TO ve CC yalnizca bu adres.')
        self.stdout.write('Konu: sevkiyat | Icerik: sevkiyat tamam (imza/ek metin olmamali)')
        if not password:
            raise CommandError('AI_EMAIL_PASSWORD tanimli degil veya bos.')
        stage = 'Son islenen mail kaydi'
        try:
            checkpoint = LastProcessEmail.objects.order_by('-id').first()
            self.stdout.write(f'Son islenen ID: {checkpoint.email_id if checkpoint else "YOK"}')
            stage = 'Exchange gelen kutusu'
            credentials = Credentials(mailbox, password)
            account = Account(
                primary_smtp_address=mailbox,
                config=Configuration(
                    service_endpoint='https://webmail.arslanaluminyum.com/EWS/Exchange.asmx',
                    credentials=credentials,
                ),
                autodiscover=False, access_type=DELEGATE,
            )
            past_checkpoint = False
            for item in account.inbox.all().order_by('-datetime_received')[:options['limit']]:
                if checkpoint and item.id == checkpoint.email_id:
                    past_checkpoint = True
                sender = getattr(getattr(item, 'sender', None), 'email_address', '')
                self.stdout.write(
                    f'{item.datetime_received} sender={sender} subject={item.subject!r} '
                    f'match={is_sevkiyat_completed(item)} '
                    f'checkpoint_veya_daha_eski={past_checkpoint}'
                )
            if options['query']:
                stage = 'SQL Server sevkiyat sorgusu'
                period, total = get_monthly_shipped_kg()
                self.stdout.write(f'Sorgu OK: {period:%m/%Y} toplam={total} kg')
                stage = 'Gunluk sevkiyat toplami'
                today, daily = get_daily_shipped_kg()
                self.stdout.write(f'Gunluk toplam OK: {today:%d.%m.%Y} toplam={daily} kg')
                stage = 'Gunluk firma ve satis pozisyonu dokumu'
                details = get_daily_shipment_breakdown(datetime.now(ZoneInfo('Europe/Istanbul')).date())
                self.stdout.write(f'Gunluk dokum OK: {len(details)} satir')
                stage = 'Aylik ilk 5 firma'
                top = get_monthly_top_shipment_firms()
                self.stdout.write(f'Aylik ilk 5 OK: {len(top)} firma')
        except Exception as exc:
            raise CommandError(f'{stage} HATA: {type(exc).__name__}: {exc}') from exc
        self.stdout.write(self.style.SUCCESS('Teshis tamamlandi. Mail gonderilmedi; kayit degistirilmedi.'))
