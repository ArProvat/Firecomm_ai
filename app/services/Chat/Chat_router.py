
import base64
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from ...DB.MongoDB.mongobd import MongoDBSessionManager as mongodb
from typing import Annotated, Optional
from ...module.voicePipeline.VoicePipeline import VoicePipeline
import json
import uuid 
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()
mongodb_init = mongodb()
voice_pipeline_instance = VoicePipeline()


@router.websocket('/ws')
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info(f"✅ Client connected: {websocket.client}")
    
    try:
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")
            logger.info(f"📥 Received message type: {message_type}")
            
            is_new_session = False
            session_id = None
            title = None  # FIXED: Initialize title
            
            try: 
                if message_type == "text":
                    text_input = data.get("payload")
                    user_id = data.get("user_id", )
                    session_id = data.get("session_id")
                    
                    if not session_id:
                        session_id = str(uuid.uuid4())
                        is_new_session = True
                    else:
                        is_new_session = False
                    
                    if not text_input:
                        raise ValueError("Text payload is required")
                    
                    logger.info(f"💬 Processing text: {text_input[:50]}...")
                    
                    async for text_chunk in roami_reassures_instance.get_response(
                        session_id=session_id,
                        user_input=text_input,
                        user_id=user_id
                    ):
                        await websocket.send_json({
                            "type": "agent_text",
                            "text": text_chunk
                        })
                    
                    await websocket.send_json({"type": "complete"})
                    logger.info("✅ Text response complete")
                    
                    if is_new_session:
                        try:
                            title = await roami_reassures_instance.generate_session_title(text_input)
                            await websocket.send_json({
                                "type": "title",
                                "title": title,
                                "session_id": session_id
                            })
                            logger.info(f"📝 Generated title: {title}")
                        except Exception as e:
                            logger.error(f"Title generation error: {e}")
                            title = "New Chat" 
                            await websocket.send_json({
                                "type": "error",
                                "message": f"Title generation error: {str(e)}"
                            })
                        
                        try:
                            await mongodb_init.create_session(user_id, session_id, title,Type="Ressures")
                            logger.info(f"💾 Session created: {session_id}")
                        except Exception as e:
                            logger.error(f"MongoDB error: {e}")
                            await websocket.send_json({
                                "type": "error",
                                "message": f"MongoDB error: {str(e)}"
                            })
                    
                elif message_type == "voice":
                    audio_data = data.get("payload")
                    user_id = data.get("user_id")
                    session_id = data.get("session_id")
                    
                    if not session_id:
                        session_id = str(uuid.uuid4())
                        is_new_session = True
                    
                    if not audio_data:
                        raise ValueError("Audio payload is required")
                    
                    logger.info("🎤 Processing voice message...")
                    
                    try:
                        audio_bytes = base64.b64decode(audio_data)
                        logger.info(f"🔊 Audio size: {len(audio_bytes)} bytes")
                    except Exception as e:
                        raise ValueError(f"Invalid base64 audio data: {str(e)}")
                    
                    async for event in voice_pipeline_instance.pipeline(
                        audio_data=audio_bytes,
                        response_function=roami_reassures_instance.get_response,
                        session_id=session_id,
                        user_id=user_id
                    ):
                        await websocket.send_json(event)
                    
                    await websocket.send_json({"type": "complete"})
                    logger.info("✅ Voice response complete")
                    
                    title = "Voice Chat"
                    
                    if is_new_session:
                        await websocket.send_json({
                            "type": "title",
                            "title": title,
                            "session_id": session_id
                        })
                        
                        try:
                            await mongodb_init.create_session(user_id, session_id, title,Type="Ressures")
                            logger.info(f"💾 Session created: {session_id}")
                        except Exception as e:
                            logger.error(f"MongoDB error: {e}")
                            await websocket.send_json({
                                "type": "error",
                                "message": f"MongoDB error: {str(e)}"
                            })
                    
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown message type: {message_type}"
                    })
                    
            except ValueError as ve:
                logger.error(f"❌ Validation error: {ve}")
                await websocket.send_json({
                    "type": "error",
                    "message": str(ve)
                })
            except Exception as msg_error:
                logger.error(f"❌ Processing error: {msg_error}")
                await websocket.send_json({
                    "type": "error",
                    "message": f"Processing error: {str(msg_error)}"
                })
                
    except WebSocketDisconnect:
        logger.info("🔌 Client disconnected normally")
    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}")
    finally:
        logger.info("👋 Closing connection")



@router.post("/reassurances/")
async def roami_reassures_endpoint(
    request: RoamiReassuresRequestSchema,
    audio: Annotated[Optional[UploadFile], File()] = None
):
    """Non-streaming endpoint"""
    try:
        user_input = request.user_input
        user_id = getattr(request, 'user_id', 'default_user')
        session_id = getattr(request, 'session_id', 'roami_reassures_session')
        
        if not user_input:
            raise HTTPException(status_code=400, detail="user_input is required")
        
        # Collect all chunks
        response_text = ""
        async for chunk in roami_reassures_instance.get_response(
            session_id=session_id,
            user_input=user_input,
            user_id=user_id
        ):
            response_text += chunk
        
        return {"response": response_text}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reassurances/stream/")
async def roami_reassures_stream_endpoint(
    user_prompt: Annotated[str, Form()],
    user_id: Annotated[str, Form()] = "default_user",
    session_id: Annotated[Optional[str], Form()] = None,
    upload_file: Annotated[Optional[UploadFile], File()] = None
):
    """Streaming endpoint"""
    try:
        if not user_prompt:
            raise HTTPException(status_code=400, detail="user_prompt is required")
        
        # Generate session_id if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
        
        return StreamingResponse(
            roami_reassures_instance.get_response(
                session_id=session_id,
                user_input=user_prompt,
                user_id=user_id
            ),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/reassurances/chat_history')
async def roami_reassures_chat_history(session_id: str, user_id: str):
    """Get chat history for a session"""
    try:
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id is required")

        history = mongodb_init.get_session_message(session_id)
        messages = [{
            "type": msg.type,      
            "content": msg.content 
        } for msg in history.messages]

        return {
            "session_id": session_id,
            "chat_history": messages,
            "message_count": len(messages)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/reassurances/sessions')
async def roami_reassures_chat_session(user_id: str,Type:str):
    """Get all sessions for a user"""
    try:
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id is required")
        
        sessions = await mongodb_init.get_session(user_id,Type)
        return {
            "user_id": user_id,
            "sessions": sessions,
            "count": len(sessions)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.delete('/ressures/sessions')
async def delete_session(session_id: str, user_id: str):
    try:
        result = await mongodb_init.delete_session(session_id.user_id)
        if result:
            return {
                "message":"Session deleted successfully",
                **result
            }

    except Exception as e :
        raise HTTPException(status_code=500,detail=str(e))