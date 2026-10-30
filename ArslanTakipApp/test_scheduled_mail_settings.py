from datetime import datetime
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.test import RequestFactory, SimpleTestCase

from .admin import MailReportSettingsAdmin
from .mail_report_settings import get_scheduled_report_recipients
from .models import MailReportSettings
from .utilities import test_report


class ScheduledMailSettingsTests(SimpleTestCase):
    def config(self, code='daily_test', **changes):
        values = dict(code=code, name='Saatli Rapor', is_active=True,
                      to_addresses='to@example.com', cc_addresses='cc@example.com',
                      sender_addresses='', test_sender_addresses='')
        values.update(changes)
        return MailReportSettings(**values)

    def test_scheduled_config_requires_no_sender_and_admin_hides_trigger_fields(self):
        config = self.config()
        config.clean()
        request = RequestFactory().get('/admin/')
        request.user = Mock()
        request.user.has_perm.return_value = True
        model_admin = MailReportSettingsAdmin(MailReportSettings, admin.site)
        form = model_admin.get_form(request, obj=config)
        self.assertNotIn('sender_addresses', form.base_fields)
        self.assertNotIn('test_sender_addresses', form.base_fields)
        self.assertIn('to_addresses', form.base_fields)
        with self.assertRaises(ValidationError):
            self.config(sender_addresses='sender@example.com').clean()

    @patch('ArslanTakipApp.mail_report_settings.get_report_settings')
    def test_recipient_changes_are_read_for_next_run(self, lookup):
        lookup.side_effect = [self.config(), self.config(to_addresses='new@example.com', cc_addresses='')]
        self.assertEqual(get_scheduled_report_recipients('daily_test'),
                         (['to@example.com'], ['cc@example.com']))
        self.assertEqual(get_scheduled_report_recipients('daily_test'), (['new@example.com'], []))

    @patch('ArslanTakipApp.utilities.test_report.KalipMs')
    @patch('ArslanTakipApp.utilities.test_report.send_email')
    @patch('ArslanTakipApp.mail_report_settings.get_report_settings')
    def test_paused_scheduled_reports_do_not_query_or_send(self, lookup, send, dies):
        lookup.return_value = self.config(is_active=False)
        test_report.send_daily_test_report_for_all()
        test_report.send_new_dies_without_orders_report()
        dies.objects.using.assert_not_called()
        send.assert_not_called()

    @patch('ArslanTakipApp.utilities.test_report.render_to_string', return_value='<p>Report</p>')
    @patch('ArslanTakipApp.utilities.test_report.KalipMs')
    @patch('ArslanTakipApp.utilities.test_report.Location')
    @patch('ArslanTakipApp.utilities.test_report.send_email', return_value=True)
    @patch('ArslanTakipApp.mail_report_settings.get_report_settings')
    def test_daily_test_uses_admin_distribution_even_for_empty_report(self, lookup, send, location, dies, render):
        lookup.return_value = self.config()
        location.objects.filter.return_value = []
        test_report.send_daily_test_report_for_all()
        lookup.assert_called_once_with('daily_test')
        self.assertEqual(send.call_args.kwargs['to_addresses'], ['to@example.com'])
        self.assertEqual(send.call_args.kwargs['cc_recipients'], ['cc@example.com'])
        self.assertTrue(send.call_args.kwargs['subject'].startswith('Güncel Test Raporu - '))

    @patch('ArslanTakipApp.utilities.test_report.render_to_string', return_value='<p>Report</p>')
    @patch('ArslanTakipApp.utilities.test_report.MusteriFirma')
    @patch('ArslanTakipApp.utilities.test_report.SiparisList')
    @patch('ArslanTakipApp.utilities.test_report.KalipMs')
    @patch('ArslanTakipApp.utilities.test_report.send_email', return_value=True)
    @patch('ArslanTakipApp.mail_report_settings.get_report_settings')
    def test_profile_report_uses_admin_distribution_only_when_data_exists(self, lookup, send, dies,
                                                                       orders, firms, render):
        lookup.return_value = self.config('profiles_without_orders')
        queryset = dies.objects.using.return_value.values.return_value.annotate.return_value.filter
        queryset.return_value = [{'ProfilNo': '1234', 'FirmaKodu': 'F1', 'CreateTime': datetime.now()}]
        orders.objects.using.return_value.filter.return_value.exists.return_value = False
        firms.objects.using.return_value.filter.return_value.values.return_value.first.return_value = None
        test_report.send_new_dies_without_orders_report()
        lookup.assert_called_once_with('profiles_without_orders')
        self.assertEqual(send.call_args.kwargs['to_addresses'], ['to@example.com'])
        self.assertEqual(send.call_args.kwargs['cc_recipients'], ['cc@example.com'])
        self.assertTrue(send.call_args.kwargs['subject'].startswith('Profil Sipariş Takip Raporu - '))
        send.reset_mock()
        queryset.return_value = []
        test_report.send_new_dies_without_orders_report()
        send.assert_not_called()

    def test_seed_keeps_both_original_distributions(self):
        migration = import_module('ArslanTakipApp.migrations.0146_scheduled_mail_report_settings')
        apps = Mock()
        migration.seed_scheduled_reports(apps, SimpleNamespace(connection=SimpleNamespace(alias='default')))
        calls = apps.get_model.return_value.objects.using.return_value.get_or_create.call_args_list
        seeds = {call.kwargs['code']: call.kwargs['defaults'] for call in calls}
        daily, profiles = seeds['daily_test'], seeds['profiles_without_orders']
        self.assertEqual(len(daily['to_addresses'].splitlines()), 16)
        self.assertEqual(len(daily['cc_addresses'].splitlines()), 6)
        self.assertEqual(profiles['to_addresses'], 'hasanpasa@arslanaluminyum.com')
        self.assertEqual(profiles['cc_addresses'].splitlines(),
                         ['ufukizgi@arslanaluminyum.com', 'yazilim@arslanaluminyum.com'])
        self.assertEqual(daily['sender_addresses'], '')
        self.assertEqual(profiles['test_sender_addresses'], '')
