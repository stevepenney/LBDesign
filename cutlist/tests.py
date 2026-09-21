from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import Organisation, User
from projects.models import Project
from .models import CutlistProject


@override_settings(STORAGES={
    'default':     {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})
class CutlistListTests(TestCase):

    def test_list_renders_when_creator_was_deleted(self):
        org = Organisation.objects.create(name='Test Merchant')
        project = Project.objects.create(organisation=org)
        CutlistProject.objects.create(project=project, created_by=None)
        staff = User.objects.create_user('lb', password='x', role=User.Role.LB_ADMIN)

        self.client.force_login(staff)
        response = self.client.get(reverse('cutlist:project_list'))

        self.assertEqual(response.status_code, 200)
