import json


from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    DataPart,
    Part,
    Task,
    TaskState,
    TextPart,
    UnsupportedOperationError,
)
from a2a.utils import (
    new_agent_parts_message,
    new_agent_text_message,
    new_task,
)
from a2a.utils.errors import ServerError
from agent import ReimbursementAgent


class ReimbursementAgentExecutor(AgentExecutor):
    """Reimbursement AgentExecutor Example."""

    def __init__(self):
        self.agent = ReimbursementAgent()

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """ 执行具体的agent_executor方法，开始向 agent 发送实际请求，进行执行具体的智能体 """
        query = context.get_user_input()
        task = context.current_task

        # This agent always produces Task objects. If this request does
        # not have current task, create a new one and use it.
        if not task:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)
        updater = TaskUpdater(event_queue, task.id, task.contextId)
        # invoke the underlying agent, using streaming results. The streams
        # now are update events.
        # 具体去执行对应 agent的方法，其中 task.contextId 是最为核心的，标识这个任务到底是如何进行执行的，也就是使用agent当中的哪个tool进行执行
        async for item in self.agent.stream(query, task.contextId):
            is_task_complete = item['is_task_complete']
            artifacts = None
            if not is_task_complete:
                await updater.update_status(
                    TaskState.working,
                    new_agent_text_message(
                        item['updates'], task.contextId, task.id
                    ),
                )
                continue
            # If the response is a dictionary, assume its a form
            if isinstance(item['content'], dict):
                # Verify it is a valid form
                if (
                    'response' in item['content']
                    and 'result' in item['content']['response']
                ):
                    data = json.loads(item['content']['response']['result'])
                    await updater.update_status(
                        TaskState.input_required,
                        new_agent_parts_message(
                            [Part(root=DataPart(data=data))],
                            task.contextId,
                            task.id,
                        ),
                        final=True,
                    )
                    continue
                else:
                    await updater.update_status(
                        TaskState.failed,
                        new_agent_text_message(
                            'Reaching an unexpected state',
                            task.contextId,
                            task.id,
                        ),
                        final=True,
                    )
                    break
            else:
                # Emit the appropriate events
                await updater.add_artifact(
                    [Part(root=TextPart(text=item['content']))], name='form'
                )
                await updater.complete()
                break

    async def cancel(
        self, request: RequestContext, event_queue: EventQueue
    ) -> Task | None:
        raise ServerError(error=UnsupportedOperationError())
