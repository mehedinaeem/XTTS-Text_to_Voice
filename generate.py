from TTS.api import TTS

tts = TTS("tts_models/en/vctk/vits")

tts.tts_to_file(
    text="""
    Welcome to this documentary.
    Today we explore one of the most fascinating mysteries in human history.
    Deep beneath the oceans and hidden within ancient civilizations,
    remarkable discoveries continue to reshape our understanding of the world.
    """,
    speaker="p266",
    file_path="output/p266_documentary.wav"
)

print("Done!")