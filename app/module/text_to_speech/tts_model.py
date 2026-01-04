import base64
from openai import AsyncOpenAI


class TTSservice:
    def __init__(self):
        self.client = AsyncOpenAI()
    
    async def generate_speech(
        self, 
        text: str, 
        voice: str = "alloy", 
        format: str = "mp3"
    ):
        """
        Generate complete speech audio and return as base64
        
        Args:
            text: Text to convert to speech
            voice: Voice to use (alloy, echo, fable, onyx, nova, shimmer)
            format: Audio format (mp3, opus, aac, flac)
            
        Returns:
            base64-encoded audio string (ready for JSON serialization)
        """
        try:
            response = await self.client.audio.speech.create(
                model="tts-1",
                voice=voice,
                response_format=format,
                input=text
            )
            
            # ✅ ALWAYS return base64-encoded string for JSON serialization
            audio_bytes = response.content
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
            return audio_base64
            
        except Exception as e:
            print(f"Error in TTS service: {str(e)}")
            raise e
    
    async def generate_speech_bytes(
        self, 
        text: str, 
        voice: str = "alloy", 
        format: str = "mp3"
    ):
        """
        Generate complete speech audio and return as raw bytes
        (Use this if you need raw bytes for file saving, etc.)
        
        Args:
            text: Text to convert to speech
            voice: Voice to use
            format: Audio format
            
        Returns:
            Raw audio bytes
        """
        try:
            response = await self.client.audio.speech.create(
                model="tts-1",
                voice=voice,
                response_format=format,
                input=text
            )
            
            return response.content
            
        except Exception as e:
            print(f"Error in TTS service: {str(e)}")
            raise e