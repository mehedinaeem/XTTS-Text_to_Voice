from django.views import View
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.contrib import messages
from apps.projects.models import Project, GeneratedAudio, GenerationHistory
from .services.tts_service import synthesis_queue
import os

class GenerateAudioView(View):
    """
    POST endpoint to submit a script segment into the background worker queue.
    """
    def post(self, request, project_id):
        project = get_object_or_404(Project, id=project_id)
        script_text = request.POST.get('script_text', '').strip()
        speaker = request.POST.get('speaker', project.voice_settings.speaker_id)
        
        if not script_text:
            return JsonResponse({'error': 'Script text cannot be blank'}, status=400)
            
        # Create audio record in database with status PENDING
        audio_record = GeneratedAudio.objects.create(
            project=project,
            script_text=script_text,
            speaker=speaker,
            status='PENDING'
        )
        
        # Enqueue synthesis task
        synthesis_queue.put({'audio_id': audio_record.id})
        
        return JsonResponse({
            'status': 'queued',
            'audio_id': str(audio_record.id),
            'message': 'Synthesis job added to queue.'
        })


class AudioStatusView(View):
    """
    GET endpoint to poll status of audio generation.
    """
    def get(self, request, audio_id):
        audio = get_object_or_404(GeneratedAudio, id=audio_id)
        return JsonResponse({
            'id': str(audio.id),
            'status': audio.status,
            'duration': audio.duration or 0,
            'error_message': audio.error_message,
            'audio_url': audio.audio_file.url if audio.audio_file else None
        })


class ViewLogsView(View):
    """
    GET endpoint to stream console logs of a specific audio generation run.
    """
    def get(self, request, audio_id):
        audio = get_object_or_404(GeneratedAudio, id=audio_id)
        try:
            history = audio.history
            log_content = history.log_content
            processing_time = history.processing_time_seconds
            system_details = history.system_details
        except Exception:
            log_content = "Logs pending..."
            processing_time = 0.0
            system_details = "Queued"
            
        return JsonResponse({
            'audio_id': str(audio.id),
            'log_content': log_content,
            'processing_time': processing_time,
            'system_details': system_details
        })


class AudioDeleteView(View):
    """
    POST/GET handler to delete generated files and database history.
    """
    def post(self, request, pk):
        audio = get_object_or_404(GeneratedAudio, pk=pk)
        project_id = audio.project.id
        
        # Delete audio file from disk
        if audio.audio_file:
            try:
                if os.path.exists(audio.audio_file.path):
                    os.remove(audio.audio_file.path)
            except Exception as e:
                print(f"[Delete] Disk deletion failed for file: {e}")
                
        audio.delete()
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == 'true':
            return JsonResponse({'status': 'deleted'})
            
        messages.success(request, "Generated audio segment deleted successfully.")
        return redirect(reverse('projects:script_editor', kwargs={'pk': project_id}))

    def get(self, request, pk):
        # Allow simple GET redirect deletions for standard HTML triggers
        return self.post(request, pk)
