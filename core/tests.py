from django.test import SimpleTestCase

from accounts.models import User
from core.templatetags.user_tags import user_label


class UserLabelTests(SimpleTestCase):

    def test_none_returns_fallback(self):
        self.assertEqual(user_label(None), '—')
        self.assertEqual(user_label(None, 'Unknown'), 'Unknown')

    def test_prefers_full_name(self):
        user = User(username='sp', first_name='Steve', last_name='Penney')
        self.assertEqual(user_label(user), 'Steve Penney')

    def test_falls_back_to_username(self):
        self.assertEqual(user_label(User(username='sp')), 'sp')
