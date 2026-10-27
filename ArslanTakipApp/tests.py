from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from .sevkiyat_report import (
    get_monthly_shipped_kg,
    is_sevkiyat_completed,
    send_sevkiyat_report,
)


class SevkiyatReportTests(SimpleTestCase):
    def message(self, **kwargs):
        values = dict(
            sender=SimpleNamespace(email_address='yazilim@arslanaluminyum.com'),
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
        self.assertFalse(is_sevkiyat_completed(self.message(
            sender=SimpleNamespace(email_address='serkankutluca@arslanaluminyum.com'),
        )))

    def test_rejects_other_subject_or_extra_body_text(self):
        self.assertFalse(is_sevkiyat_completed(self.message(subject='Re: sevkiyat')))
        self.assertFalse(is_sevkiyat_completed(self.message(text_body='sevkiyat tamam değil')))
        self.assertFalse(is_sevkiyat_completed(self.message(text_body='')))

    def test_html_body_fallback(self):
        self.assertTrue(is_sevkiyat_completed(self.message(
            text_body=None, body='<div>sevkiyat&nbsp;tamam</div>',
        )))

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

    @patch.dict('os.environ', {'SEVKIYAT_REPORT_TO': ''})
    def test_requires_recipients_before_querying(self):
        with self.assertRaisesRegex(ValueError, 'SEVKIYAT_REPORT_TO'):
            send_sevkiyat_report()

    @patch.dict('os.environ', {}, clear=True)
    @patch('ArslanTakipApp.email_utils.send_email', return_value=True)
    @patch('ArslanTakipApp.sevkiyat_report.get_monthly_shipped_kg',
           return_value=(datetime(2026, 10, 1), 125.5))
    def test_default_report_recipient_is_yazilim(self, monthly, send):
        send_sevkiyat_report()
        self.assertEqual(send.call_args.args[0], ['yazilim@arslanaluminyum.com'])

    @patch.dict('os.environ', {'SEVKIYAT_REPORT_TO': 'recipient@example.com'})
    @patch('ArslanTakipApp.email_utils.send_email', return_value=False)
    @patch('ArslanTakipApp.sevkiyat_report.get_monthly_shipped_kg',
           return_value=(datetime(2026, 10, 1), 125.5))
    def test_send_failure_is_not_silenced(self, monthly, send):
        with self.assertRaises(RuntimeError):
            send_sevkiyat_report()
