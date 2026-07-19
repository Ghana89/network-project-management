from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import UserProfile


class AuthFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='jdoe', email='jdoe@example.com', password='secret123')
        UserProfile.objects.create(user=self.user, role='viewer')

    def test_login_accepts_email_instead_of_username(self):
        response = self.client.post(reverse('login'), {'username': self.user.email, 'password': 'secret123'})

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('dashboard'))

    @patch('app.views.send_mail')
    def test_forgot_password_sends_reset_link(self, mock_send_mail):
        response = self.client.post(reverse('forgot_password'), {'email': self.user.email})

        self.assertEqual(response.status_code, 200)
        mock_send_mail.assert_called_once()
        self.assertEqual(mock_send_mail.call_args[0][3], [self.user.email])
