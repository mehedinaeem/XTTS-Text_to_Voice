from django.contrib import admin
from .models import Project, VoiceSettings, GeneratedAudio, GenerationHistory

admin.site.register(Project)
admin.site.register(VoiceSettings)
admin.site.register(GeneratedAudio)
admin.site.register(GenerationHistory)
