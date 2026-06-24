from django.urls import path
from . import views

app_name = 'projects'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('projects/', views.ProjectListView.as_view(), name='project_list'),
    path('projects/new/', views.ProjectCreateView.as_view(), name='project_create'),
    path('projects/<uuid:pk>/', views.ProjectDetailView.as_view(), name='project_detail'),
    path('projects/<uuid:pk>/edit/', views.ProjectUpdateView.as_view(), name='project_edit'),
    path('projects/<uuid:pk>/delete/', views.ProjectDeleteView.as_view(), name='project_delete'),
    path('projects/<uuid:pk>/editor/', views.ScriptEditorView.as_view(), name='script_editor'),
    path('projects/<uuid:pk>/import-txt/', views.ImportScriptView.as_view(), name='import_script'),
    path('settings/', views.GlobalSettingsView.as_view(), name='settings'),
]
