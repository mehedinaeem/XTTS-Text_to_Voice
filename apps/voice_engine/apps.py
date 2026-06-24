from django.apps import AppConfig


class VoiceEngineConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.voice_engine'

    def ready(self):
        # Spawns a background thread listening to incoming queue tasks on Django startup
        import threading
        from .services.tts_service import tts_worker
        t = threading.Thread(target=tts_worker, daemon=True, name="TTS-Synthesizer-Worker")
        t.start()
