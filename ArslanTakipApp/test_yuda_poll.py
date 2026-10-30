import json
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase

from . import views


class YudaPollTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.groups = MagicMock()
        self.group = SimpleNamespace(pk=20)
        self.groups.filter.return_value.first.return_value = self.group
        self.enterContext(patch.object(views, 'get_yuda_voting_groups', return_value=self.groups))
        self.votes = self.enterContext(patch.object(views.YudaOnay, 'objects'))
        self.votes.filter.return_value.count.return_value = 1
        self.yudas = self.enterContext(patch.object(views.YudaForm, 'objects'))
        self.statuses = self.enterContext(patch.object(views.YudaOnayDurum, 'objects'))
        self.enterContext(patch.object(views.transaction, 'atomic', side_effect=nullcontext))
        self.yuda = self.yudas.select_for_update.return_value.get.return_value
        self.yuda.Silindi = False
        self.statuses.filter.return_value.values.return_value = [{
            'kaliphane_onay_durumu': 2, 'mekanik_islem_onay_durumu': 0,
            'satis_onay_durumu': 2,
        }]

    def vote(self, **params):
        request = self.factory.post('/yudaDetailAnket', {'params': json.dumps({
            'yId': 42, 'secim': 'onay', **params,
        })})
        request.user = SimpleNamespace(is_authenticated=True)
        return views.yudaDetailAnket(request)

    def test_multiple_groups_require_explicit_selection(self):
        self.groups.count.return_value = 2
        self.assertEqual(self.vote().status_code, 400)
        self.votes.filter.assert_not_called()

    def test_unauthorized_group_cannot_vote(self):
        self.groups.filter.return_value.first.return_value = None
        self.assertEqual(self.vote(group_id=99).status_code, 403)
        self.votes.filter.assert_not_called()

    def test_selected_department_receives_vote(self):
        self.votes.filter.return_value.first.return_value = None
        response = self.vote(group_id=20)
        self.assertEqual(response.status_code, 200)
        self.groups.filter.assert_called_once_with(pk=20)
        self.votes.create.assert_called_once_with(Group=self.group, Yuda_id=42, OnayDurumu=True)
        self.assertEqual(json.loads(response.content)['group_id'], 20)

    def test_existing_department_vote_can_change_to_rejection(self):
        existing = self.votes.filter.return_value.first.return_value
        self.assertEqual(self.vote(group_id=20, secim='ret').status_code, 200)
        self.assertIs(existing.OnayDurumu, False)
        existing.save.assert_called_once()
        self.votes.create.assert_not_called()

    def test_single_department_is_automatic(self):
        self.groups.count.return_value = 1
        self.groups.first.return_value = self.group
        self.assertEqual(self.vote().status_code, 200)

    def test_invalid_choice_and_deleted_yuda_do_not_write(self):
        self.assertEqual(self.vote(group_id=20, secim='invalid').status_code, 400)
        self.yuda.Silindi = True
        self.assertEqual(self.vote(group_id=20).status_code, 400)
        self.votes.filter.assert_not_called()

    def test_get_cannot_change_votes(self):
        request = self.factory.get('/yudaDetailAnket')
        request.user = SimpleNamespace(is_authenticated=True)
        self.assertEqual(views.yudaDetailAnket(request).status_code, 405)
        self.votes.filter.assert_not_called()

    def test_context_retains_separate_department_decisions(self):
        self.groups.values.return_value = [{'id': 20, 'name': 'Sales'}, {'id': 30, 'name': 'Quality'}]
        self.votes.filter.return_value.order_by.return_value.values_list.return_value = [(20, True), (30, False)]
        groups = views.yuda_poll_context(SimpleNamespace(), 42)['voting_groups']
        self.assertEqual([group['vote'] for group in groups], [True, False])

    def test_templates_render_department_selector(self):
        for count in (0, 1, 2):
            groups = [{'id': i, 'name': 'Bölüm', 'vote': None} for i in range(count)]
            html = render_to_string('ArslanTakipApp/yudaPollGroups.html', {'voting_groups': groups})
            self.assertIn('yudaVotingGroup', html)
            self.assertEqual('Bölüm seçiniz' in html, count != 1)
