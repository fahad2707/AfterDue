from fastapi import APIRouter, HTTPException, Response, status

from app.domain.enums import ReasonCode
from app.routes.deps import Ingest
from app.schemas.events import EventIn, IngestResponse
from app.services.event_ingest import Outcome

router = APIRouter(prefix="/api", tags=["events"])

#: Rejections that mean "this event can never apply", as opposed to a
#: transient conflict. Everything here answers 409.
_CONFLICT_CODES = {
    ReasonCode.ILLEGAL_TRANSITION,
    ReasonCode.STALE_EVENT,
    ReasonCode.CONCURRENT_MODIFICATION,
    ReasonCode.DUPLICATE_INVOICE,
    ReasonCode.DUPLICATE_BILLING_CYCLE,
    ReasonCode.RUN_ID_MISMATCH,
}


@router.post("/events", response_model=IngestResponse)
async def post_event(event_in: EventIn, ingest: Ingest, response: Response):
    """Ingest one payment-platform event.

    The route is deliberately thin: validate, delegate, map the outcome onto a
    status code. All ledger logic lives in the service.

    A duplicate answers 200 rather than an error — redelivery is normal for
    at-least-once webhooks, and the caller's correct reaction is to stop
    retrying, not to alert.
    """
    result = await ingest.ingest(event_in)

    if result.reason_code is ReasonCode.UNKNOWN_SUBSCRIPTION:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"unknown subscription {event_in.subscription_id}",
        )

    if result.outcome is Outcome.REJECTED:
        response.status_code = (
            status.HTTP_409_CONFLICT if result.reason_code in _CONFLICT_CODES else 422
        )

    return IngestResponse(
        event_id=result.event_id,
        outcome=result.outcome.value,
        reason_code=result.reason_code,
        subscription=result.subscription.model_dump() if result.subscription else None,
    )
