from django.urls import path
from . import views

app_name = 'cutlist'

urlpatterns = [
    path('',                              views.project_list,      name='project_list'),
    path('new/<int:project_pk>/',         views.project_new,       name='project_new'),
    path('<int:pk>/',                     views.project_edit,      name='project_edit'),
    path('<int:pk>/save/',                views.project_save,      name='project_save'),
    path('<int:pk>/delete/',              views.project_delete,    name='project_delete'),
    path('<int:pk>/duplicate/',           views.project_duplicate, name='project_duplicate'),
    path('<int:pk>/print/',               views.project_print,     name='project_print'),
]
