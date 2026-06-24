import threading
import queue
import time
import os
from TTS.api import TTS
from django.conf import settings
from apps.projects.models import GeneratedAudio, GenerationHistory

class TTSEngineManager:
    """
    Singleton wrapper around the Coqui TTS Engine.
    Ensures model weights are only loaded once and access is thread-safe.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(TTSEngineManager, cls).__new__(cls)
                    cls._instance.initialized = False
                    cls._instance.tts_model = None
        return cls._instance

    def initialize(self, model_name="tts_models/en/vctk/vits"):
        if self.initialized:
            return
        with self._lock:
            if not self.initialized:
                print(f"[TTS-Engine] Loading model: {model_name}...")
                # Initialize Coqui TTS (loads weights to memory/GPU if available)
                self.tts_model = TTS(model_name)
                self.initialized = True
                print("[TTS-Engine] Model loaded successfully.")

    def synthesize(self, text, speaker, output_path):
        """
        Executes TTS synthesis. Must be called inside a thread lock to prevent concurrent PyTorch access.
        """
        if not self.initialized:
            self.initialize()
        
        with self._lock:
            start_time = time.time()
            # Perform Coqui TTS file generation
            self.tts_model.tts_to_file(
                text=text,
                speaker=speaker,
                file_path=output_path
            )
            duration = time.time() - start_time
            return duration


# Global thread-safe queue for processing incoming speech requests
synthesis_queue = queue.Queue()

def tts_worker():
    """
    Background worker loop. Consumes tasks from the queue one by one,
    ensures clean execution logs, and updates the database states.
    """
    print("[TTS-Worker] Background thread listener started.")
    engine = TTSEngineManager()
    
    while True:
        try:
            # Blocks indefinitely until a task is available
            task = synthesis_queue.get()
            audio_id = task['audio_id']
            
            # Fetch record
            try:
                audio_record = GeneratedAudio.objects.get(id=audio_id)
            except GeneratedAudio.DoesNotExist:
                synthesis_queue.task_done()
                continue
            
            # Transition status
            audio_record.status = 'PROCESSING'
            audio_record.save()
            
            # Determine paths
            output_filename = f"{audio_record.project.id}_{audio_id}.wav"
            output_dir = os.path.join(settings.MEDIA_ROOT, 'generated_audio')
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, output_filename)
            
            # Run synthesis
            start_perf = time.time()
            log_output = []
            try:
                # Lazy-load engine weights if not done
                engine.initialize(model_name=audio_record.project.voice_settings.model_name)
                log_output.append(f"Model initialization check passed at {time.time()}")
                
                # Execute TTS
                inference_duration = engine.synthesize(
                    text=audio_record.script_text,
                    speaker=audio_record.speaker,
                    output_path=output_path
                )
                
                # Calculate audio duration using soundfile to find actual duration in seconds
                import soundfile as sf
                f = sf.SoundFile(output_path)
                actual_duration_seconds = len(f) / f.samplerate
                f.close()
                
                # Update Audio Record
                audio_record.audio_file = f"generated_audio/{output_filename}"
                audio_record.duration = round(actual_duration_seconds, 2)
                audio_record.status = 'COMPLETED'
                audio_record.error_message = None
                audio_record.save()
                
                # Save Log
                processing_time = time.time() - start_perf
                GenerationHistory.objects.create(
                    generated_audio=audio_record,
                    log_content="\n".join(log_output) + f"\n[Success] Synthesis finished in {processing_time:.2f} seconds.\nInference duration: {inference_duration:.2f}s",
                    processing_time_seconds=processing_time,
                    system_details=f"Speaker: {audio_record.speaker} | Length: {audio_record.character_count} chars"
                )
                
            except Exception as e:
                import traceback
                error_trace = traceback.format_exc()
                
                audio_record.status = 'FAILED'
                audio_record.error_message = str(e)
                audio_record.save()
                
                processing_time = time.time() - start_perf
                GenerationHistory.objects.create(
                    generated_audio=audio_record,
                    log_content=f"[Error] TTS Synthesis failed:\n{error_trace}",
                    processing_time_seconds=processing_time,
                    system_details="FAILED"
                )
                
            finally:
                synthesis_queue.task_done()
                
        except Exception as q_err:
            print(f"[TTS-Worker] Queue exception encountered: {q_err}")
            time.sleep(2)
