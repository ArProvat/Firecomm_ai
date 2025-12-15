import io
from openai import OpenAI
from ...config.config import settings


class STTservice:
    def __init__(self,):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    async def transcribe_speech(self, audio_data: bytes ) -> str:

        try:
            audio_file = io.BytesIO(audio_data)
            audio_file.name = "audio.webm" 
            

            response = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
            return response.text
        
        except Exception as e:
            raise e