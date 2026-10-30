from datetime import date, datetime
from zoneinfo import ZoneInfo
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, RequestFactory, override_settings

from .models import MailReportSettings

from .sevkiyat_report import (
    get_monthly_shipped_kg,
    get_daily_shipped_kg,
    get_daily_shipment_breakdown,
    get_monthly_top_shipment_firms,
    get_shipment_groups,
    is_sevkiyat_completed,
    send_sevkiyat_report,
)


class SevkiyatReportTests(SimpleTestCase):
    def setUp(self):
        super().setUp()
        self.mail_settings = MailReportSettings(
            code='sevkiyat', name='Sevkiyat Raporu', is_active=True,
            to_addresses='recipient1@example.com\nrecipient2@example.com',
            cc_addresses='cc@example.com',
            sender_addresses='serkankutluca@arslanaluminyum.com\nfurkankaya@arslanaluminyum.com\nyazilim@arslanaluminyum.com',
            test_sender_addresses='yazilim@arslanaluminyum.com',
        )
        self.settings_lookup = self.enterContext(patch(
            'ArslanTakipApp.sevkiyat_report.get_sevkiyat_settings', return_value=self.mail_settings,
        ))

    def message(self, **kwargs):
        values = dict(
            sender=SimpleNamespace(email_address='serkankutluca@arslanaluminyum.com'),
            subject='sevkiyat', text_body='sevkiyat tamam', body='',
        )
        values.update(kwargs)
        return SimpleNamespace(**values)

    def test_matches_normalized_subject_and_body(self):
        self.assertTrue(is_sevkiyat_completed(self.message(
            subject=' SEVKİYAT ', text_body=' SEVKİYAT \n TAMAM ',
        )))

    def test_rejects_other_sender(self):
        self.assertFalse(is_sevkiyat_completed(self.message(
            sender=SimpleNamespace(email_address='other@example.com'),
        )))

    def test_furkan_triggers_same_report_conditions(self):
        sender = SimpleNamespace(email_address='FURKANKAYA@arslanaluminyum.com')
        self.assertTrue(is_sevkiyat_completed(self.message(sender=sender)))
        self.assertFalse(is_sevkiyat_completed(self.message(sender=sender, subject='baska konu')))
        self.assertFalse(is_sevkiyat_completed(self.message(sender=sender, text_body='devam ediyor')))

    def test_yazilim_matches_uppercase_subject_and_body(self):
        self.assertTrue(is_sevkiyat_completed(self.message(
            sender=SimpleNamespace(email_address='YAZILIM@arslanaluminyum.com'),
            subject='SEVKİYAT', text_body='SEVKİYAT TAMAM',
        )))

    def test_rejects_other_subject_or_extra_body_text(self):
        self.assertFalse(is_sevkiyat_completed(self.message(subject='Re: sevkiyat')))
        self.assertFalse(is_sevkiyat_completed(self.message(text_body='sevkiyat tamam değil')))
        self.assertFalse(is_sevkiyat_completed(self.message(text_body='')))

    def test_html_body_fallback(self):
        self.assertTrue(is_sevkiyat_completed(self.message(
            text_body=None, body='<div>sevkiyat&nbsp;tamam</div>',
        )))

    @patch('ArslanTakipApp.email_utils.LastProcessEmail')
    @patch('ArslanTakipApp.email_utils.Account')
    @patch('ArslanTakipApp.sevkiyat_report.send_sevkiyat_report')
    def test_incoming_mail_passes_sent_timestamp_to_report(self, report, account, checkpoint):
        from ArslanTakipApp.email_utils import check_new_emails
        sent = datetime(2026, 10, 26, 20, tzinfo=ZoneInfo('UTC'))
        message = self.message(id='new-mail', datetime_sent=sent,
                               datetime_received=datetime(2026, 10, 27, tzinfo=ZoneInfo('UTC')))
        checkpoint.objects.latest.return_value.email_id = 'previous-mail'
        inbox = account.return_value.inbox
        inbox.filter.return_value.only.return_value.order_by.return_value = [
            message, SimpleNamespace(id='previous-mail'),
        ]
        inbox.get.return_value = message
        check_new_emails()
        inbox.filter.return_value.only.assert_called_once_with('subject', 'datetime_received')
        inbox.get.assert_called_once_with(id='new-mail')
        report.assert_called_once_with(shipment_datetime=sent,
                                       sender_email='serkankutluca@arslanaluminyum.com')
        checkpoint.objects.create.assert_called_once_with(email_id='new-mail')

    @patch('ArslanTakipApp.email_utils.LastProcessEmail')
    @patch('ArslanTakipApp.email_utils.Account')
    @patch('ArslanTakipApp.sevkiyat_report.send_sevkiyat_report')
    def test_unrelated_mail_does_not_download_body(self, report, account, checkpoint):
        from ArslanTakipApp.email_utils import check_new_emails
        inbox = account.return_value.inbox
        checkpoint.objects.latest.return_value.email_id = 'previous-mail'
        inbox.filter.return_value.only.return_value.order_by.return_value = [
            SimpleNamespace(id='other-mail', subject='Başka konu',
                            datetime_received=datetime(2026, 10, 27)),
            SimpleNamespace(id='previous-mail'),
        ]
        check_new_emails()
        inbox.get.assert_not_called()
        report.assert_not_called()
        checkpoint.objects.create.assert_called_once_with(email_id='other-mail')

    def test_december_boundary_and_total(self):
        with patch('ArslanTakipApp.sevkiyat_report.SevkiyatFaturaListesi') as view, \
                patch('ArslanTakipApp.sevkiyat_report.Firma'), \
                patch('ArslanTakipApp.sevkiyat_report.UrunCikisi') as shipments:
            shipments.objects.using.return_value.filter.return_value.aggregate.return_value = {'total': 125.5}
            start, total = get_monthly_shipped_kg(datetime(2026, 12, 15))
            filters = view.objects.using.return_value.filter.call_args.kwargs
            self.assertEqual(start, datetime(2026, 12, 1))
            self.assertEqual(filters['Tarih__lt'], datetime(2027, 1, 1))
            self.assertEqual(filters['SevkEdildi'], 'EVET')
            self.assertEqual(total, 125.5)

    @patch.dict('os.environ', {}, clear=True)
    @patch('ArslanTakipApp.sevkiyat_report.get_monthly_top_shipment_firms',
           return_value=[{'Firma': 'ÖRNEK ALÜMİNYUM SANAYİ VE TİCARET A.Ş.', 'TOPLAM': 500.0}])
    @patch('ArslanTakipApp.sevkiyat_report.get_daily_shipment_breakdown', return_value=[])
    @patch('ArslanTakipApp.sevkiyat_report.get_daily_shipped_kg',
           return_value=(datetime(2026, 10, 26), 25.0))
    @patch('ArslanTakipApp.email_utils.send_email', return_value=True)
    @patch('ArslanTakipApp.sevkiyat_report.get_monthly_shipped_kg',
           return_value=(datetime(2026, 10, 1), 125.5))
    def test_report_uses_sender_date_and_production_distribution(self, monthly, send, daily, detail, top):
        with patch('ArslanTakipApp.sevkiyat_report.datetime') as clock:
            clock.now.return_value = datetime(2026, 10, 27, 17, 0, tzinfo=ZoneInfo('Europe/Istanbul'))
            send_sevkiyat_report(datetime(2026, 10, 26, 20, 0, tzinfo=ZoneInfo('UTC')))
        self.assertEqual(send.call_args.args[0], self.mail_settings.addresses('to_addresses'))
        self.assertEqual(send.call_args.args[1], self.mail_settings.addresses('cc_addresses'))
        self.assertEqual(len(set(send.call_args.args[0])), 2)
        self.assertEqual(len(set(send.call_args.args[1])), 1)
        self.assertNotIn('yazilim@arslanaluminyum.com', send.call_args.args[0])
        self.assertEqual(send.call_args.args[2], 'Sevkiyat Raporu - 27/10/2026 17:00')
        self.assertIn('27.10.2026', send.call_args.args[3])
        self.assertIn('Günlük Sevk Edilen', send.call_args.args[3])
        self.assertIn('26.10.2026', send.call_args.args[3])
        detail.assert_called_once_with(date(2026, 10, 26))
        self.assertIn('Bu Ay En Çok Sevkiyat Yapılan 5 Firma', send.call_args.args[3])
        self.assertIn('ÖRNEK ALÜMİNYUM SANAYİ', send.call_args.args[3])
        self.assertNotIn('VE TİCARET A.Ş.', send.call_args.args[3])
        self.assertNotIn('Sayın İlgili', send.call_args.args[3])
        self.assertNotIn('Türkiye saati', send.call_args.args[3])
        self.assertIn('27.10.2026 saat 17:00 itibarıyla', send.call_args.args[3])
        self.assertIn('otomatik olarak oluşturulmuş', send.call_args.args[3])
        self.assertNotIn('[Ad Soyad]', send.call_args.args[3])
        self.assertNotIn('Sevkiyat tamam bildirimi alındı.', send.call_args.args[3])
        attachment = send.call_args.kwargs['attachments'][0]
        self.assertEqual(attachment[0], 'Sevkiyat_Raporu_2026-10-27_17-00.pdf')
        self.assertTrue(attachment[1].startswith(b'%PDF-'))
        self.assertEqual(attachment[2], 'application/pdf')
        daily.assert_called_once_with(datetime(2026, 10, 26, 23, 0, tzinfo=ZoneInfo('Europe/Istanbul')))
        # Test mailinde gerçek dağıtım listesi TO veya CC'ye sızmamalı.
        send_sevkiyat_report(sender_email=' YAZILIM@arslanaluminyum.com ')
        self.assertEqual(send.call_args.args[0], ['yazilim@arslanaluminyum.com'])
        self.assertEqual(send.call_args.args[1], ['yazilim@arslanaluminyum.com'])
        for sender in ('serkankutluca@arslanaluminyum.com', 'furkankaya@arslanaluminyum.com'):
            send_sevkiyat_report(sender_email=sender)
            self.assertEqual(send.call_args.args[0], self.mail_settings.addresses('to_addresses'))
            self.assertEqual(send.call_args.args[1], self.mail_settings.addresses('cc_addresses'))
        self.mail_settings.to_addresses = 'new-recipient@example.com'
        self.mail_settings.cc_addresses = 'new-copy@example.com'
        send_sevkiyat_report(sender_email='serkankutluca@arslanaluminyum.com')
        self.assertEqual(send.call_args.args[0], ['new-recipient@example.com'])
        self.assertEqual(send.call_args.args[1], ['new-copy@example.com'])
        self.assertNotIn('cid:sevkiyat-logo', send.call_args.args[3])
        self.assertNotIn('Deneme:', send.call_args.args[3])
        self.assertIn('GÜNLÜK SEVKİYAT TOPLAMI', send.call_args.args[3])

    @patch('ArslanTakipApp.email_utils.Account')
    @patch('ArslanTakipApp.email_utils.Message')
    def test_mail_attaches_pdf_before_sending(self, message, account):
        from .email_utils import send_email
        self.assertTrue(send_email(['recipient@example.com'], [], 'Test', 'Body',
                                  attachments=[('report.pdf', b'%PDF-test', 'application/pdf')]))
        attached = message.return_value.attach.call_args.args[0]
        self.assertEqual(attached.name, 'report.pdf')
        self.assertEqual(attached.content, b'%PDF-test')
        message.return_value.send.assert_called_once_with()

    @patch('ArslanTakipApp.sevkiyat_report.get_monthly_top_shipment_firms', return_value=[])
    @patch('ArslanTakipApp.sevkiyat_report.get_daily_shipment_breakdown', return_value=[])
    @patch('ArslanTakipApp.sevkiyat_report.get_daily_shipped_kg',
           return_value=(datetime(2026, 10, 27), 0.0))
    @patch('ArslanTakipApp.email_utils.send_email', return_value=False)
    @patch('ArslanTakipApp.sevkiyat_report.get_monthly_shipped_kg',
           return_value=(datetime(2026, 10, 1), 125.5))
    def test_send_failure_is_not_silenced(self, monthly, send, daily, detail, top):
        with self.assertRaises(RuntimeError):
            send_sevkiyat_report()

    @patch('ArslanTakipApp.sevkiyat_report.get_shipped_kg', return_value=0.0)
    def test_daily_uses_turkey_date_and_next_day_exclusive(self, total):
        start, kg = get_daily_shipped_kg(datetime(2026, 12, 31, 22, tzinfo=ZoneInfo('UTC')))
        self.assertEqual(start, datetime(2027, 1, 1))
        total.assert_called_once_with(datetime(2027, 1, 1), datetime(2027, 1, 2))
        self.assertEqual(kg, 0.0)

    def test_breakdown_filters_and_groups_like_sql(self):
        with patch('ArslanTakipApp.sevkiyat_report.SevkiyatRaporu') as view, \
                patch('ArslanTakipApp.sevkiyat_report.UrunCikisi') as shipments:
            normalized = shipments.objects.using.return_value.filter.return_value.order_by.return_value
            grouped = normalized.values.return_value
            grouped.annotate.return_value = [
                {'FirmaAdi': 'Firma A', 'SatisPozisyon': 'Yurtici', 'TOPLAM': 100.0},
            ]
            rows = get_daily_shipment_breakdown(date(2026, 10, 26))
            filters = shipments.objects.using.return_value.filter.call_args.kwargs
            self.assertEqual(filters['Tarih__gte'], datetime(2026, 10, 26))
            self.assertEqual(filters['Tarih__lt'], datetime(2026, 10, 27))
            self.assertEqual(filters['SevkEdildi'], 'EVET')
            view.objects.using.return_value.filter.assert_called_once_with(KartTuru__isnull=False)
            view.objects.using.return_value.filter.return_value.exclude.assert_called_once_with(KartTuru='Fason')
            normalized.values.assert_called_once_with('FirmaAdi', 'SatisPozisyon')
            self.assertEqual(rows[0]['TOPLAM'], 100.0)

    @patch('ArslanTakipApp.sevkiyat_report.get_shipment_groups')
    def test_monthly_top_five_combines_sales_positions(self, groups):
        groups.return_value = [{'Firma': f'Firma {i}', 'TOPLAM': 100-i} for i in range(7)]
        rows = get_monthly_top_shipment_firms(datetime(2026, 12, 31))
        groups.assert_called_once_with(datetime(2026, 12, 1), datetime(2027, 1, 1))
        self.assertEqual(rows, groups.return_value[:5])

    @patch('ArslanTakipApp.sevkiyat_report.get_shipment_queryset')
    def test_normalized_firms_are_merged_after_sql_aggregation(self, shipments):
        raw = shipments.return_value.order_by.return_value.values.return_value.annotate
        raw.return_value = [
            {'FirmaAdi': 'Alumeco A', 'SatisPozisyon': 'Yurt İçi', 'TOPLAM': 100.0},
            {'FirmaAdi': 'ALUMECO B', 'SatisPozisyon': 'Yurt İçi', 'TOPLAM': 200.0},
            {'FirmaAdi': 'Alumeco A', 'SatisPozisyon': 'İhracat', 'TOPLAM': 50.0},
            {'FirmaAdi': 'PERPOLIO A', 'SatisPozisyon': 'Yurt İçi', 'TOPLAM': 40.0},
            {'FirmaAdi': 'ALUFORTİS B', 'SatisPozisyon': 'Yurt İçi', 'TOPLAM': 60.0},
            {'FirmaAdi': 'ALUFORTIS C', 'SatisPozisyon': 'Yurt İçi', 'TOPLAM': 20.0},
            {'FirmaAdi': 'Boş Toplam', 'SatisPozisyon': None, 'TOPLAM': None},
        ]
        start, end = datetime(2026, 10, 26), datetime(2026, 10, 27)
        daily = get_shipment_groups(start, end, by_sales_position=True)
        self.assertEqual(daily[0], {'Firma': 'Alumeco', 'SatisPozisyon': 'Yurt İçi', 'TOPLAM': 300.0})
        self.assertEqual(daily[1]['Firma'], 'PERPOLIO/ALUFORTİS')
        self.assertEqual(daily[1]['TOPLAM'], 120.0)
        self.assertEqual(daily[2]['TOPLAM'], 50.0)
        self.assertIsNone(daily[-1]['TOPLAM'])
        monthly = get_shipment_groups(start, end)
        self.assertEqual(monthly[0], {'Firma': 'Alumeco', 'TOPLAM': 350.0})
        self.assertEqual(monthly[1]['TOPLAM'], 120.0)


class HomepageHasNoEmailTriggerTests(SimpleTestCase):
    @override_settings(DEBUG=False)
    @patch('ArslanTakipApp.sevkiyat_report.send_sevkiyat_report')
    def test_homepage_never_sends_mail(self, send):
        from .views import IndexView
        request = RequestFactory().get('/', REMOTE_ADDR='127.0.0.1')
        view = IndexView()
        view.setup(request)
        context = view.get_context_data()
        self.assertNotIn('local_sevkiyat_report_status', context)
        send.assert_not_called()

    @override_settings(DEBUG=True, ALLOWED_HOSTS=['127.0.0.1'])
    @patch('ArslanTakipApp.sevkiyat_report.send_sevkiyat_report')
    def test_local_home_never_sends_mail(self, send):
        from .views import IndexView
        request = RequestFactory().get('/', HTTP_HOST='127.0.0.1', REMOTE_ADDR='127.0.0.1')
        request.session = {}
        view = IndexView()
        view.setup(request)
        self.assertNotIn('local_sevkiyat_report_status', view.get_context_data())
        view.get_context_data()
        send.assert_not_called()
