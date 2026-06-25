from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('feedback/', views.submit_feedback, name='submit_feedback'),
    path('help/<slug:slug>/', views.help_topic, name='help_topic'),
]
