from importlib import import_module
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.contrib import admin
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.test import RequestFactory, SimpleTestCase

from .admin import MailReportSettingsAdmin
from .mail_report_settings import get_sevkiyat_settings, parse_email_addresses
from .models import MailReportSettings
from .sevkiyat_report import is_sevkiyat_completed, send_sevkiyat_report


class MailReportSettingsTests(SimpleTestCase):
    def settings(self, **overrides):
        fields = dict(
            code='sevkiyat', name='Sevkiyat Raporu', is_active=True,
            to_addresses='one@example.com', cc_addresses='',
            sender_addresses='sender@example.com\ntest@example.com',
            test_sender_addresses='test@example.com',
        )
        fields.update(overrides)
        return MailReportSettings(**fields)

    def message(self, sender='sender@example.com'):
        return SimpleNamespace(
            sender=SimpleNamespace(email_address=sender),
            subject='SEVKİYAT', text_body='SEVKİYAT TAMAM', body='',
        )

    def test_address_formats_normalize_and_deduplicate(self):
        self.assertEqual(parse_email_addresses(
            ' ONE@example.com; two@example.com,\nONE@example.com '
        ), ['one@example.com', 'two@example.com'])

    def test_active_report_requires_valid_to_and_sender_lists(self):
        for field in ('to_addresses', 'sender_addresses'):
            config = self.settings(**{field: ''}, test_sender_addresses='')
            with self.subTest(field=field), self.assertRaises(ValidationError) as exc:
                config.clean()
            self.assertIn(field, exc.exception.message_dict)
        with self.assertRaises(ValidationError) as exc:
            self.settings(cc_addresses='not-an-email').clean()
        self.assertIn('cc_addresses', exc.exception.message_dict)

    def test_test_senders_must_be_allowed(self):
        with self.assertRaises(ValidationError) as exc:
            self.settings(test_sender_addresses='other@example.com').clean()
        self.assertIn('test_sender_addresses', exc.exception.message_dict)

    def test_clean_stores_one_normalized_address_per_line(self):
        config = self.settings(to_addresses=' ONE@example.com; one@example.com, TWO@example.com')
        config.clean()
        self.assertEqual(config.to_addresses, 'one@example.com\ntwo@example.com')

    @patch('ArslanTakipApp.sevkiyat_report.get_sevkiyat_settings')
    @patch('ArslanTakipApp.email_utils.send_email')
    @patch('ArslanTakipApp.sevkiyat_report.get_monthly_shipped_kg')
    def test_disabled_report_neither_matches_nor_sends(self, query, send, lookup):
        lookup.return_value = self.settings(is_active=False)
        self.assertFalse(is_sevkiyat_completed(self.message()))
        self.assertFalse(send_sevkiyat_report(sender_email='sender@example.com'))
        query.assert_not_called()
        send.assert_not_called()

    @patch('ArslanTakipApp.sevkiyat_report.get_sevkiyat_settings')
    @patch('ArslanTakipApp.email_utils.send_email')
    def test_removed_sender_cannot_send(self, send, lookup):
        lookup.return_value = self.settings()
        self.assertFalse(is_sevkiyat_completed(self.message('removed@example.com')))
        self.assertFalse(send_sevkiyat_report(sender_email='removed@example.com'))
        send.assert_not_called()

    @patch('ArslanTakipApp.sevkiyat_report.get_sevkiyat_settings')
    def test_changed_sender_list_is_used_on_next_check(self, lookup):
        lookup.side_effect = [self.settings(sender_addresses='other@example.com'), self.settings()]
        self.assertFalse(is_sevkiyat_completed(self.message()))
        self.assertTrue(is_sevkiyat_completed(self.message()))

    @patch('ArslanTakipApp.models.MailReportSettings.objects')
    def test_lookup_reads_default_database_every_time(self, manager):
        manager.using.return_value.get.side_effect = [self.settings(name='First'), self.settings(name='Second')]
        self.assertEqual(get_sevkiyat_settings().name, 'First')
        self.assertEqual(get_sevkiyat_settings().name, 'Second')
        self.assertEqual(manager.using.return_value.get.call_count, 2)
        manager.using.assert_called_with('default')

    @patch('ArslanTakipApp.models.MailReportSettings.objects')
    def test_missing_record_does_not_fall_back_to_old_recipients(self, manager):
        manager.using.return_value.get.side_effect = MailReportSettings.DoesNotExist
        with self.assertRaises(ImproperlyConfigured):
            get_sevkiyat_settings()

    def test_seed_preserves_current_distribution_and_test_rule(self):
        migration = import_module('ArslanTakipApp.migrations.0144_mailreportsettings')
        apps, editor = Mock(), SimpleNamespace(connection=SimpleNamespace(alias='default'))
        migration.seed_sevkiyat_settings(apps, editor)
        create = apps.get_model.return_value.objects.using.return_value.get_or_create
        seed = create.call_args.kwargs['defaults']
        self.assertEqual(len(parse_email_addresses(seed['to_addresses'])), 29)
        self.assertEqual(len(parse_email_addresses(seed['cc_addresses'])), 7)
        self.assertIn('kevsermolla@arslanaluminyum.com', seed['to_addresses'])
        self.assertEqual(seed['test_sender_addresses'], 'yazilim@arslanaluminyum.com')
        self.assertEqual(create.call_args.kwargs['code'], 'sevkiyat')

    def test_admin_validates_lists_and_uses_model_permissions(self):
        model_admin = MailReportSettingsAdmin(MailReportSettings, admin.site)
        request = RequestFactory().get('/admin/')
        request.user = Mock()
        request.user.has_perm.return_value = False
        self.assertFalse(model_admin.has_change_permission(request))
        request.user.has_perm.return_value = True
        self.assertTrue(model_admin.has_change_permission(request))
        self.assertFalse(model_admin.has_add_permission(request))
        self.assertFalse(model_admin.has_delete_permission(request))
        config = self.settings()
        form_class = model_admin.get_form(request, obj=config)
        data = dict(name='Sevkiyat', is_active='on', to_addresses='invalid-address',
                    sender_addresses='sender@example.com')
        form = form_class(data=data, instance=config)
        self.assertFalse(form.is_valid())
        self.assertIn('to_addresses', form.errors)
        data['to_addresses'] = 'New@Example.com; new@example.com'
        valid_form = form_class(data=data, instance=self.settings())
        self.assertTrue(valid_form.is_valid(), valid_form.errors)
        self.assertEqual(valid_form.instance.to_addresses, 'new@example.com')
