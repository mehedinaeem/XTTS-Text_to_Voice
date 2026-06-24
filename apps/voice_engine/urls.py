from django.urls import path
from . import views

app_name = 'voice_engine'

urlpatterns = [
    path('generate/<uuid:project_id>/', views.GenerateAudioView.as_view(), name='generate_audio'),
    path('status/<uuid:audio_id>/', views.AudioStatusView.as_view(), name='audio_status'),
    path('history/<uuid:audio_id>/logs/', views.ViewLogsView.as_view(), name='view_logs'),
    path('audio/<uuid:pk>/delete/', views.AudioDeleteView.as_view(), name='delete_audio'),
]
