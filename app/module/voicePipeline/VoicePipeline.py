import base64
import time
import asyncio
from typing import Any, Callable, AsyncGenerator, List, Optional
from ..speech_to_text.stt_model import STTservice
from ..text_to_speech.tts_model import TTSservice


class VoicePipeline:
    def __init__(self):
        self.stt_service = STTservice()
        self.tts_service = TTSservice()
        
        self.pending_tts_task: Optional[asyncio.Task] = None
        self.last_buffer = ""
        
    async def pipeline(
        self,
        audio_data: bytes,
        response_function: Callable[..., AsyncGenerator[str, None]],
        session_id: str,
        user_id: str,
        stt_format: str = "wav",
        tts_voice: str = "alloy",
        tts_format: str = "mp3",
        enable_parallel_tts: bool = True,
        enable_preemptive_tts: bool = True,
    ):
        """
        Advanced voice pipeline with multiple optimizations
        
        Args:
            audio_data: Raw audio bytes
            response_function: Async generator function
            session_id: Session identifier
            user_id: User identifier
            enable_parallel_tts: Generate multiple audio chunks in parallel
            enable_preemptive_tts: Start TTS before sentence completes
        """
        try:
            # Step 1: Speech to Text
            stt_start = time.time()
            transcript = await self.stt_service.transcribe_speech(audio_data)
            stt_latency = time.time() - stt_start
            
            yield {
                "type": "stt_output",
                "text": transcript,
                "latency": stt_latency,
                "timestamp": time.time()
            }

            buffer = ""
            sentences_to_generate: List[str] = []
            
            # Step 2: Get agent response
            async for text_chunk in response_function(
                session_id=session_id,
                user_input=transcript,
                user_id=user_id
            ):
                if not text_chunk:  
                    continue
                    
                # Always yield text for display
                yield {"type": "agent_text", "text": text_chunk}
                buffer += text_chunk

                # Pre-emptive TTS: Start generating audio speculatively
                if enable_preemptive_tts and self._should_start_preemptive(buffer):
                    await self._start_preemptive_tts(
                        buffer, tts_voice, tts_format
                    )

                # Check if we have complete sentences to generate
                if self._should_generate_audio(buffer):
                    text_to_speak = buffer.strip()
                    buffer = ""
                    
                    # Cancel pre-emptive task if it was for wrong text
                    if self.pending_tts_task and text_to_speak != self.last_buffer:
                        self.pending_tts_task.cancel()
                        self.pending_tts_task = None
                    
                    # Use pre-emptive result if available
                    if self.pending_tts_task and text_to_speak == self.last_buffer:
                        try:
                            audio_base64 = await self.pending_tts_task
                            yield {
                                "type": "tts_audio",
                                "audio": audio_base64,
                                "format": tts_format,
                                "timestamp": time.time(),
                                "preemptive": True
                            }
                            self.pending_tts_task = None
                            continue
                        except asyncio.CancelledError:
                            pass
                    
                    # Add to parallel generation queue
                    if enable_parallel_tts:
                        sentences_to_generate.append(text_to_speak)
                        
                        # Generate in parallel when we have multiple sentences
                        if len(sentences_to_generate) >= 2:
                            async for audio_result in self._generate_parallel_audio(
                                sentences_to_generate, tts_voice, tts_format
                            ):
                                yield audio_result
                            sentences_to_generate = []
                    else:
                        # Sequential generation
                        tts_start = time.time()
                        audio_base64 = await self.tts_service.generate_speech(
                            text=text_to_speak,
                            voice=tts_voice,
                            format=tts_format
                        )
                        tts_latency = time.time() - tts_start
                        
                        yield {
                            "type": "tts_audio",
                            "audio": audio_base64,
                            "format": tts_format,
                            "timestamp": time.time(),
                            "latency": tts_latency
                        }

            # Generate remaining sentences in parallel
            if sentences_to_generate:
                async for audio_result in self._generate_parallel_audio(
                    sentences_to_generate, tts_voice, tts_format
                ):
                    yield audio_result
            
            if buffer.strip():
                tts_start = time.time()
                audio_base64 = await self.tts_service.generate_speech(
                    text=buffer.strip(),
                    voice=tts_voice,
                    format=tts_format
                )
                tts_latency = time.time() - tts_start
                
                yield {
                    "type": "tts_audio",
                    "audio": audio_base64,
                    "format": tts_format,
                    "timestamp": time.time(),
                    "latency": tts_latency
                }

        except Exception as e:
            print(f"Error in voice pipeline: {str(e)}")
            raise e
        finally:
            if self.pending_tts_task:
                self.pending_tts_task.cancel()
                self.pending_tts_task = None
    
    async def _generate_parallel_audio(
        self, 
        sentences: List[str], 
        voice: str, 
        format: str
    ):
        """Generate audio for multiple sentences in parallel"""
        print(f"🚀 Generating {len(sentences)} audio chunks in parallel")
        
        tasks = []
        for sentence in sentences:
            task = asyncio.create_task(
                self._generate_with_timing(sentence, voice, format)
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Error generating audio for sentence {i}: {result}")
                continue
            
            audio_base64, latency = result
            yield {
                "type": "tts_audio",
                "audio": audio_base64,
                "format": format,
                "timestamp": time.time(),
                "latency": latency,
                "parallel": True,
                "batch_size": len(sentences)
            }
    
    async def _generate_with_timing(self, text: str, voice: str, format: str):
        """Generate audio and track timing"""
        start = time.time()
        audio = await self.tts_service.generate_speech(text, voice, format)
        latency = time.time() - start
        return audio, latency
    
    async def _start_preemptive_tts(self, buffer: str, voice: str, format: str):
        """Start generating audio speculatively before sentence completes"""
        if self.pending_tts_task:
            self.pending_tts_task.cancel()
        
        self.last_buffer = buffer.strip()
        self.pending_tts_task = asyncio.create_task(
            self.tts_service.generate_speech(
                text=self.last_buffer,
                voice=voice,
                format=format
            )
        )
        print(f"🔮 Pre-emptive TTS started for: '{self.last_buffer[:30]}...'")
    
    def _should_start_preemptive(self, buffer: str) -> bool:
        """
        Decide if we should start pre-emptive TTS
        Start when we have most of a sentence but not quite done
        """
        stripped = buffer.rstrip()
        word_count = len(buffer.split())
        
        
        if 6 <= word_count <= 10 and not self.pending_tts_task:
            return True
        
        if stripped.endswith(",") and word_count >= 5 and not self.pending_tts_task:
            return True
        
        return False
    
    def _should_generate_audio(self, buffer: str) -> bool:
        """Determine if buffer is ready for definite TTS generation"""
        stripped = buffer.rstrip()
        
        if stripped.endswith((".", "!", "?")):
            return True
        
        if stripped.endswith(",") and len(buffer.split()) >= 8:
            return True
        
        if len(buffer.split()) >= 12:
            return True
        
        return False