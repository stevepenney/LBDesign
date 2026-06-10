from django.urls import path
from . import views

app_name = 'projects'

urlpatterns = [
    path('',                            views.project_list,         name='project_list'),
    path('new/',                        views.project_create,       name='project_create'),
    path('<int:pk>/',                   views.project_detail,       name='project_detail'),
    path('<int:pk>/edit/',              views.project_edit,         name='project_edit'),
    path('<int:pk>/promote/',           views.project_promote,      name='project_promote'),
    path('<int:pk>/discard/',           views.project_discard,      name='project_discard'),
    path('<int:pk>/undiscard/',         views.project_undiscard,    name='project_undiscard'),
    path('<int:pk>/update-field/',      views.project_update_field, name='project_update_field'),
    path('<int:pk>/request-quote/',     views.project_request_quote, name='request_quote'),
    path('<int:pk>/documents/add/',      views.document_add,          name='document_add'),
    path('<int:pk>/documents/upload/',   views.document_upload_ajax,  name='document_upload'),
    path('<int:pk>/documents/<int:doc_pk>/delete/', views.document_delete, name='document_delete'),
]
