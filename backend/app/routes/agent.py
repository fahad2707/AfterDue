from fastapi import APIRouter, HTTPException, Query, status

from app.routes.deps import Agent
from app.schemas.agent import ExecuteRequest, PlanRequest

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/cases/{case_id}/plan")
async def plan_case(case_id: str, agent: Agent, body: PlanRequest | None = None):
    prefer = body.prefer_llm if body else False
    try:
        return await agent.plan(case_id, prefer_llm=prefer)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown recovery case") from None


@router.post("/cases/{case_id}/execute")
async def execute_case(case_id: str, agent: Agent, body: ExecuteRequest | None = None):
    prefer = body.prefer_llm if body else False
    key = body.idempotency_key if body else None
    try:
        return await agent.execute(case_id, prefer_llm=prefer, idempotency_key=key)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown recovery case") from None


@router.get("/runs/{agent_run_id}")
async def get_agent_run(agent_run_id: str, agent: Agent):
    record = await agent.agent_runs.get(agent_run_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown agent run")
    actions = await agent.actions.list_for_agent(agent_run_id)
    return {
        **record.model_dump(),
        "actions": [a.model_dump() for a in actions],
        "synthetic": True,
        "simulated": True,
    }


@router.get("/cases/{case_id}/plan")
async def plan_case_get(
    case_id: str,
    agent: Agent,
    prefer_llm: bool = Query(default=False),
):
    try:
        return await agent.plan(case_id, prefer_llm=prefer_llm)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown recovery case") from None
