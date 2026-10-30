from importlib import import_module
from types import SimpleNamespace
from unittest.mock import Mock, PropertyMock, patch

from django.contrib import admin
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.test import RequestFactory, SimpleTestCase

from .admin import MailReportRouteInline, MailReportSettingsAdmin
from .mail_report_settings import get_event_report_recipients
from .models import MailReportRoute, MailReportSettings
from .utilities import test_report


class EventMailSettingsTests(SimpleTestCase):
    def setUp(self):
        self.config = MailReportSettings(pk=1, code='die_transfer', name='Transfer', is_active=True,
                                         to_addresses='common@example.com', cc_addresses='copy@example.com',
                                         include_actor=True)
        self.route = MailReportRoute(report=self.config, route_key='1100-1', is_active=True,
                                     to_addresses='press@example.com\ncommon@example.com',
                                     cc_addresses='copy@example.com\npress-copy@example.com')
        self.routes = Mock()
        self.routes.using.return_value.filter.return_value.first.return_value = self.route
        self.enterContext(patch.object(MailReportSettings, 'routes', new_callable=PropertyMock,
                                      return_value=self.routes))
        self.lookup = self.enterContext(patch('ArslanTakipApp.mail_report_settings.get_report_settings',
                                             return_value=self.config))

    def test_transfer_combines_common_route_and_actor_without_duplicates(self):
        self.assertEqual(get_event_report_recipients('die_transfer', ' 1100-1 ', actor_email='Actor@Example.com'),
                         (['common@example.com', 'press@example.com', 'actor@example.com'],
                          ['copy@example.com', 'press-copy@example.com']))
        self.routes.using.return_value.filter.assert_called_with(route_key='1100-1')

    def test_dynamic_representative_can_be_enabled_or_disabled(self):
        self.config.code = 'die_test'
        self.config.include_actor = False
        self.config.include_representative = True
        kwargs = dict(actor_email='actor@example.com',
                      representative_emails=['rep@example.com', 'press@example.com'])
        to, cc = get_event_report_recipients('die_test', '1100-1', **kwargs)
        self.assertEqual(to, ['common@example.com', 'press@example.com', 'rep@example.com'])
        self.config.include_representative = False
        to, cc = get_event_report_recipients('die_test', '1100-1', **kwargs)
        self.assertNotIn('rep@example.com', to)
        self.assertNotIn('actor@example.com', to)

    def test_report_and_route_can_pause_all_recipients(self):
        self.config.is_active = False
        self.assertIsNone(get_event_report_recipients('die_transfer', '1100-1', actor_email='actor@example.com'))
        self.routes.using.assert_not_called()
        self.config.is_active = True
        self.route.is_active = False
        self.assertIsNone(get_event_report_recipients('die_transfer', '1100-1', actor_email='actor@example.com'))

    def test_unknown_transfer_target_preserves_common_distribution_but_test_requires_route(self):
        self.routes.using.return_value.filter.return_value.first.return_value = None
        self.assertEqual(get_event_report_recipients('die_transfer', 'unknown', actor_email='actor@example.com'),
                         (['common@example.com', 'actor@example.com'], ['copy@example.com']))
        with self.assertRaises(ImproperlyConfigured):
            get_event_report_recipients('die_test', 'unknown')

    def test_route_edits_are_used_on_next_call_and_actor_can_be_removed(self):
        get_event_report_recipients('die_transfer', '1100-1')
        self.route.to_addresses = 'new-press@example.com'
        self.route.cc_addresses = ''
        self.config.include_actor = False
        self.assertEqual(get_event_report_recipients('die_transfer', '1100-1', actor_email='actor@example.com'),
                         (['common@example.com', 'new-press@example.com'], ['copy@example.com']))

    def test_route_validates_and_normalizes_addresses(self):
        self.route.route_key = ' 1100-1 '
        self.route.to_addresses = 'PRESS@example.com; press@example.com'
        self.route.clean()
        self.assertEqual(self.route.route_key, '1100-1')
        self.assertEqual(self.route.to_addresses, 'press@example.com')
        self.route.cc_addresses = 'bad-address'
        with self.assertRaises(ValidationError):
            self.route.clean()

    def test_event_admin_exposes_dynamic_controls_and_pres_inline(self):
        model_admin = MailReportSettingsAdmin(MailReportSettings, admin.site)
        request = RequestFactory().get('/admin/')
        request.user = Mock()
        request.user.has_perm.return_value = True
        self.assertEqual(model_admin.get_inlines(request, self.config), [MailReportRouteInline])
        form = model_admin.get_form(request, obj=self.config)
        self.assertIn('include_actor', form.base_fields)
        self.assertNotIn('sender_addresses', form.base_fields)
        self.config.code = 'die_test'
        self.config.include_actor = False
        form = model_admin.get_form(request, obj=self.config)
        self.assertIn('include_representative', form.base_fields)
        self.assertNotIn('include_actor', form.base_fields)
        self.config.to_addresses = ''
        self.config.clean()  # Pres satırları alıcı sağlayabilir; ortak TO zorunlu değil.


class EventMailPipelineTests(SimpleTestCase):
    @patch('ArslanTakipApp.views.render_to_string', return_value='<p>Transfer</p>')
    @patch('ArslanTakipApp.views.get_user_full_name', return_value='Test User')
    @patch('ArslanTakipApp.views.send_email', return_value=True)
    @patch('ArslanTakipApp.views.get_event_report_recipients')
    def test_transfer_uses_configured_distribution_and_can_skip(self, recipients, send, user, render):
        from .views import send_email_notification
        request = SimpleNamespace(user=SimpleNamespace(id=1, email='actor@example.com'))
        recipients.return_value = (['configured@example.com'], ['copy@example.com'])
        send_email_notification(request, ['D1'], '1100-1')
        recipients.assert_called_once_with('die_transfer', '1100-1', actor_email='actor@example.com')
        self.assertEqual(send.call_args.kwargs['to_addresses'], ['configured@example.com'])
        send.reset_mock()
        recipients.return_value = None
        send_email_notification(request, ['D1'], '1100-1')
        send.assert_not_called()

    @patch('ArslanTakipApp.utilities.test_report.render_to_string', return_value='<p>Test</p>')
    @patch('ArslanTakipApp.utilities.test_report.SiparisList')
    @patch('ArslanTakipApp.utilities.test_report.User')
    @patch('ArslanTakipApp.utilities.test_report.MusteriFirma')
    @patch('ArslanTakipApp.utilities.test_report.send_email', return_value=True)
    @patch('ArslanTakipApp.utilities.test_report.get_event_report_recipients')
    @patch('ArslanTakipApp.utilities.test_report.get_report_settings')
    def test_single_die_passes_representative_to_admin_routing(self, lookup, recipients, send, firms,
                                                              users, orders, render):
        config = MailReportSettings(code='die_test', is_active=True, include_representative=True)
        lookup.return_value = config
        recipients.return_value = (['configured@example.com', 'rep@example.com'], ['cc@example.com'])
        firms.objects.using.return_value.filter.return_value.values.return_value.first.return_value = {
            'MusteriTemsilcisi': 'Ali Temsilci',
        }
        candidates = users.objects.filter.return_value.filter.return_value
        candidates.exists.return_value = True
        candidates.values.return_value = [{'email': 'rep@example.com'}]
        orders.objects.using.return_value.filter.return_value.exists.return_value = False
        die = SimpleNamespace(ProfilNo='P1', FirmaKodu='F1', KalipNo='D1')
        test_report.send_single_die_report(die, '1100-1', 'Test User')
        recipients.assert_called_once_with('die_test', '1100-1', representative_emails=['rep@example.com'],
                                           report_settings=config)
        self.assertEqual(send.call_args.kwargs['to_addresses'], ['configured@example.com', 'rep@example.com'])
        send.reset_mock()
        config.is_active = False
        test_report.send_single_die_report(die, '1100-1', 'Test User')
        send.assert_not_called()
        config.is_active = True
        firms.objects.using.return_value.filter.return_value.values.return_value.first.return_value = None
        recipients.reset_mock()
        test_report.send_single_die_report(die, '1100-1', 'Test User')
        self.assertEqual(recipients.call_args.kwargs['representative_emails'], [])

    def test_seed_preserves_12_transfer_targets_and_8_test_pres_lists(self):
        migration = import_module('ArslanTakipApp.migrations.0147_event_mail_report_settings')
        seeds = {code: (defaults, routes) for code, defaults, routes in migration.EVENT_REPORT_SEEDS}
        transfer, targets = seeds['die_transfer']
        tests, presses = seeds['die_test']
        self.assertEqual(len(targets), 12)
        self.assertEqual(len(presses), 8)
        self.assertTrue(transfer['include_actor'])
        self.assertTrue(tests['include_representative'])
        self.assertEqual(transfer['to_addresses'], 'hasanpasa@arslanaluminyum.com')
        self.assertEqual(len(transfer['cc_addresses'].splitlines()), 14)
        self.assertEqual(targets['1100-1']['to_addresses'], 'eski1100pres@arslanaluminyum.com')
        self.assertIn('planlama1@arslanaluminyum.com', presses['1100-1']['to_addresses'])
