import httpx

from fastapi import FastAPI
from sse_starlette import EventSourceResponse
from multiagent.agents.host_agent import HostAgent, create_host_agent
from multiagent.agents.host_agent import TaskCallbackArg
from a2a.types import AgentCard, Task

from multiagent.agents.models.request.chat import ChatRequest
from multiagent.agents.server import base_sse_wrapper

app = FastAPI(docs_url=None, redoc_url=None)


def task_callback(task: TaskCallbackArg, agent_card: AgentCard) -> Task | None:
    print(task)
    print(agent_card)
    return None


host_agent: HostAgent | None = None


@app.on_event("startup")
async def startup_event():
    global host_agent
    remote_agent_addresses = [
        'http://localhost:10000',
        'http://localhost:10001'
    ]
    client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
    host_agent = await create_host_agent(  # 使用你之前定义的异步工厂函数
        remote_agent_addresses=remote_agent_addresses,
        http_client=client,
        task_callback=task_callback
    )


@app.post('/chat/stream', response_class=EventSourceResponse)
async def chat_stream(request: ChatRequest):
    return EventSourceResponse(
        base_sse_wrapper(host_agent.chat_stream, request)(),
        media_type="text/event-stream"
    )


if __name__ == '__main__':
    import uvicorn

    uvicorn.run("main:multiagent", host="0.0.0.0", port=8090)
