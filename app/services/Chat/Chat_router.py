from typing import Annotated, Optional
from ..Chat_schema import FirecommChatRequestSchema
from fastapi import APIRouter,HTTPException, UploadFile, File,Form, WebSocket
from fastapi.responses   import StreamingResponse





router =APIRouter()


@router.post('/chat')
async def chatRouter(request:FirecommChatRequestSchema,audio: Annotated[Optional[UploadFile], File()] = None):
    try:
        if type == "text":
            return StreamingResponse(
                text_pipeline_function(
                    roami_reassures_chain.get_chain,
                    user_input,
                    session_id="roami_reassures_session"
                ),
                media_type="text/plain",  # Changed from text/event-stream,
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )
        elif type == "audio":
            raise HTTPException(status_code=501, detail="Audio type not implemented yet")

        else:
            raise HTTPException(status_code=400, detail="Invalid type. Must be 'text' or 'audio'")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



