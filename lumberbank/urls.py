from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('accounts.urls', namespace='accounts')),
    path('projects/', include('projects.urls', namespace='projects')),
    path('jobs/', include('jobs.urls', namespace='jobs')),
    path('core/', include('core.urls', namespace='core')),
    path('cutlist/', include('cutlist.urls', namespace='cutlist')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
