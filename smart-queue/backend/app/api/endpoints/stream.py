import json
import asyncio
from uuid import UUID
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse

from app.services.broadcaster import broadcaster

router = APIRouter()

@router.get("/user/{user_id}")
async def stream_user_events(user_id: UUID, request: Request):
    """
    Step 9 Server-Sent Events (SSE) stream for real-time citizen notifications and queue turn alerts.
    """
    queue = broadcaster.subscribe_user(str(user_id))

    async def event_generator():
        try:
            # Initial connection confirmation
            init_payload = json.dumps({"event": "CONNECTED", "user_id": str(user_id)})
            yield f"data: {init_payload}\n\n"

            while True:
                if await request.is_disconnected():
                    break

                try:
                    data = await asyncio.wait_for(queue.get(), timeout=2.0)
                    if isinstance(data, dict) and data.get("event") == "CLOSE":
                        break
                    yield f"data: {json.dumps(data)}\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            broadcaster.unsubscribe_user(str(user_id), queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/branch/{branch_id}")
async def stream_branch_events(branch_id: UUID, request: Request):
    """
    Step 9 Server-Sent Events (SSE) stream for real-time staff dashboards and branch display screens.
    """
    queue = broadcaster.subscribe_branch(str(branch_id))

    async def event_generator():
        try:
            init_payload = json.dumps({"event": "CONNECTED", "branch_id": str(branch_id)})
            yield f"data: {init_payload}\n\n"

            while True:
                if await request.is_disconnected():
                    break

                try:
                    data = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"data: {json.dumps(data)}\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        finally:
            broadcaster.unsubscribe_branch(str(branch_id), queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
