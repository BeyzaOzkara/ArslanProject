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

    def test_templates_render_one_independent_card_per_department(self):
        for count in (0, 1, 2):
            groups = [{'id': i, 'name': 'Bölüm', 'vote': None} for i in range(count)]
            html = render_to_string('ArslanTakipApp/yudaPollGroups.html', {'voting_groups': groups})
            self.assertEqual(html.count('data-yuda-vote-card='), count)
            self.assertEqual(html.count('data-vote-submit'), count)
            self.assertNotIn('<select', html)
            for group in groups:
                self.assertEqual(html.count('name="yudaVote%s"' % group['id']), 2)

    def test_cards_render_saved_decisions_and_unvoted_state(self):
        html = render_to_string('ArslanTakipApp/yudaPollGroups.html', {'voting_groups': [
            {'id': 20, 'name': 'Boyahane Bolumu', 'vote': True},
            {'id': 30, 'name': 'Paketleme Bolumu', 'vote': False},
            {'id': 40, 'name': 'Kalite Bolumu', 'vote': None},
        ]})
        from html.parser import HTMLParser

        class CheckedInputs(HTMLParser):
            checked = []

            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag == 'input' and 'checked' in attrs:
                    self.checked.append(attrs['id'])

        parser = CheckedInputs()
        parser.feed(html)
        self.assertEqual(parser.checked, ['yudaOnay20', 'yudaRet30'])

    def test_successive_votes_for_two_departments_remain_independent(self):
        departments = {
            20: SimpleNamespace(pk=20, name='Boyahane Bolumu'),
            30: SimpleNamespace(pk=30, name='Paketleme Bolumu'),
        }
        stored_votes = {}
        self.groups.filter.side_effect = lambda pk: SimpleNamespace(first=lambda: departments.get(pk))

        def create_vote(Group, Yuda_id, OnayDurumu):
            vote = SimpleNamespace(OnayDurumu=OnayDurumu, save=lambda: None)
            stored_votes[(Yuda_id, Group.pk)] = vote
            return vote

        def filter_votes(Yuda_id, Group=None, OnayDurumu=None):
            if Group is not None:
                return SimpleNamespace(first=lambda: stored_votes.get((Yuda_id, Group.pk)))
            return SimpleNamespace(count=lambda: sum(
                vote.OnayDurumu is OnayDurumu
                for (yuda_id, _), vote in stored_votes.items() if yuda_id == Yuda_id
            ))

        self.votes.create.side_effect = create_vote
        self.votes.filter.side_effect = filter_votes
        first = self.vote(group_id=20)
        self.assertEqual(first.status_code, 200)
        second = self.vote(group_id=30)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(json.loads(second.content)['onay'], 2)
        third = self.vote(group_id=30, secim='ret')
        self.assertEqual(third.status_code, 200)
        result = json.loads(third.content)
        self.assertEqual((result['onay'], result['ret']), (1, 1))
        self.assertIs(stored_votes[(42, 20)].OnayDurumu, True)
        self.assertIs(stored_votes[(42, 30)].OnayDurumu, False)
        self.assertEqual(len(stored_votes), 2)
