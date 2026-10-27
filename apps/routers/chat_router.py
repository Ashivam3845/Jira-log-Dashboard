"""Chat bot endpoints."""

from fastapi import APIRouter, Depends

from apps.core.security import get_current_user
from apps.dto.api_resp import APIResponse
from apps.dto.summary_dto import ChatRequest
from apps.modules.ai_summary.chat_service import ChatEngine

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post("", response_model=APIResponse)
def chat(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    engine = ChatEngine(current_user["user_id"])
    result = engine.chat(request.message)

    if result.get("status") == "error":
        return APIResponse(success=False, message=result.get("message", "Error"), statusCode=500)

    return APIResponse(data=result, message="Chat response generated successfully")
