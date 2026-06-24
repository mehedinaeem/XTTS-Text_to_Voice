from TTS.api import TTS

tts = TTS("tts_models/en/vctk/vits")

speakers = ["p232", "p251", "p265", "p266", "p267", "p330"]

for spk in speakers:
    tts.tts_to_file(
        text="Welcome to this documentary. Today we explore one of the most fascinating mysteries in human history.",
        speaker=spk,
        file_path=f"output/{spk}.wav"
    )