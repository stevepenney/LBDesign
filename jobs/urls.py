from django.urls import path
from . import views

app_name = 'jobs'

urlpatterns = [
    # Jobs
    path('',                views.job_list,   name='job_list'),
    path('new/',            views.job_create, name='job_create'),
    path('<int:pk>/',       views.job_detail, name='job_detail'),
    path('<int:pk>/edit/',  views.job_edit,   name='job_edit'),

    path('<int:pk>/recalculate/', views.job_recalculate, name='job_recalculate'),

    # Sections (nested under a job)
    path('<int:job_pk>/sections/new/',              views.section_create, name='section_create'),
    path('<int:job_pk>/sections/<int:pk>/edit/',    views.section_edit,   name='section_edit'),
    path('<int:job_pk>/sections/<int:pk>/delete/',  views.section_delete, name='section_delete'),
]
