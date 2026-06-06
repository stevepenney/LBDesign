from django.urls import path
from . import views

app_name = 'jobs'

urlpatterns = [
    path('quick/',                    views.estimate_quick, name='estimate_quick'),
    path('new/<int:project_pk>/',     views.job_create,    name='job_create'),
    path('<int:pk>/',                 views.job_detail, name='job_detail'),
    path('<int:pk>/edit/',            views.job_edit,   name='job_edit'),

    path('<int:pk>/update-field/',    views.job_update_field, name='job_update_field'),
    path('<int:pk>/recalculate/',     views.job_recalculate,  name='job_recalculate'),
    path('<int:pk>/duplicate/',       views.job_duplicate,   name='job_duplicate'),

    # Sections (nested under an estimate)
    path('<int:job_pk>/sections/new/',              views.section_create, name='section_create'),
    path('<int:job_pk>/sections/<int:pk>/edit/',    views.section_edit,   name='section_edit'),
    path('<int:job_pk>/sections/<int:pk>/delete/',  views.section_delete, name='section_delete'),
]
