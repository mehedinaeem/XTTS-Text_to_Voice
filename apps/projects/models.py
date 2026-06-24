import uuid
from django.db import models

class Project(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, help_text="Title of the documentary project")
    description = models.TextField(blank=True, null=True, help_text="Optional project summary")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.name

    @property
    def total_audio_duration(self):
        successful_audio = self.generated_audios.filter(status='COMPLETED')
        return sum(audio.duration for audio in successful_audio if audio.duration)


class VoiceSettings(models.Model):
    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name='voice_settings')
    model_name = models.CharField(max_length=150, default="tts_models/en/vctk/vits")
    speaker_id = models.CharField(max_length=100, default="p266")
    speed = models.FloatField(default=1.0, help_text="Speech speed modifier (0.5 to 2.0)")
    pitch = models.FloatField(default=1.0, help_text="Speech pitch modifier (if supported by backend)")
    output_format = models.CharField(max_length=10, default="wav")
    output_directory = models.CharField(max_length=500, blank=True, null=True)

    def __str__(self):
        return f"Voice Settings for {self.project.name} ({self.speaker_id})"


class GeneratedAudio(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Queued'),
        ('PROCESSING', 'Synthesizing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='generated_audios')
    script_text = models.TextField(help_text="The chunk of text passed to the TTS engine")
    audio_file = models.FileField(upload_to='generated_audio/', blank=True, null=True)
    speaker = models.CharField(max_length=100)
    word_count = models.PositiveIntegerField(default=0)
    character_count = models.PositiveIntegerField(default=0)
    duration = models.FloatField(null=True, blank=True, help_text="Length of generated audio in seconds")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.project.name} - {self.speaker} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    def save(self, *args, **kwargs):
        if self.script_text:
            self.character_count = len(self.script_text)
            self.word_count = len(self.script_text.split())
        super().save(*args, **kwargs)


class GenerationHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    generated_audio = models.OneToOneField(GeneratedAudio, on_delete=models.CASCADE, related_name='history')
    log_content = models.TextField(blank=True, null=True, help_text="Captured console output or traceback logs")
    processing_time_seconds = models.FloatField(default=0.0, help_text="Total processing time in seconds")
    system_details = models.CharField(max_length=255, blank=True, null=True, help_text="CPU/GPU usage statistics during run")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Log {self.id} for Audio {self.generated_audio.id}"
