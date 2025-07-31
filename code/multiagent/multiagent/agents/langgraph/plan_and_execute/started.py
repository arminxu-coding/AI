"""
官方示例代码
"""
import asyncio
import json
import operator
from typing import Annotated, List, Tuple, Union, Literal
from typing_extensions import TypedDict

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from langchain_community.tools import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate


class PlanExecute(TypedDict):
    input: str
    plan: List[str]
    past_steps: Annotated[List[Tuple], operator.add]
    response: str


class Plan(BaseModel):
    """Plan to follow in future"""

    steps: List[str] = Field(
        description="different steps to follow, should be in sorted order"
    )


class Response(BaseModel):
    """Response to user."""

    response: str


class Act(BaseModel):
    """Action to perform."""

    action: Union[Response, Plan] = Field(
        description="Action to perform. If you want to respond to user, use Response. "
                    "If you need to further use tools to get the answer, use Plan."
    )


load_dotenv()

tools = [TavilySearchResults(max_results=3)]

llm = ChatOpenAI(model="deepseek/deepseek-chat-v3-0324:free")

prompt = "You are a helpful assistant."
agent_executor = create_react_agent(llm, tools, prompt=prompt)

# resp = agent_executor.invoke({
#     "messages": [
#         ("user", "who is the winnner of the us open")
#     ]
# })
# print(resp)


planner_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """对于给定的目标，制定一个简单的分步计划。这个计划应该包括单独的任务，如果执行得当，就会得到正确的答案。不要添加任何多余的步骤。\
            最后一步的结果应该是最终答案。确保每个步骤都有所需的所有信息，不要跳过步骤。""",
        ),
        ("placeholder", "{messages}"),
    ]
)
planner = planner_prompt | ChatOpenAI(
    model="deepseek/deepseek-chat-v3-0324:free", temperature=0
).with_structured_output(Plan)

# resp = planner.invoke(
#     {
#         "messages": [
#             ("user", "what is the hometown of the current Australia open winner?")
#         ]
#     }
# )
# print(resp)

replanner_prompt = ChatPromptTemplate.from_template("""对于给定的目标，制定一个简单的分步计划。\
这个计划应该包括单独的任务，如果执行得当，就会得到正确的答案。不要添加任何多余的步骤。\
最后一步的结果应该是最终答案。确保每个步骤都有所需的所有信息，不要跳过步骤。
你的目标是：
｛input｝

你最初的计划是：
｛plan｝

你目前已经完成了以下步骤：
｛past_steps｝

相应地更新你的计划。如果不需要更多步骤，并且您可以返回给用户，那么请以该步骤进行响应。否则，填写计划。只在计划中添加仍然需要完成的步骤。不要将之前完成的步骤作为计划的一部分。""")
replanner = replanner_prompt | ChatOpenAI(
    model="deepseek/deepseek-chat-v3-0324:free", temperature=0
).with_structured_output(Act)


async def execute_step(state: PlanExecute):
    plan = state["plan"]
    plan_str = "\n".join(f"{i + 1}. {step}" for i, step in enumerate(plan))
    task = plan[0]
    task_formatted = f"对于以下计划：{plan_str}\n\n您的任务是执行步骤 {1}, {task}."
    agent_response = await agent_executor.ainvoke({
        "messages": [
            ("user", task_formatted)
        ]
    })
    return {"past_steps": [(task, agent_response["messages"][-1].content)]}


async def plan_step(state: PlanExecute):
    """
    规划整个任务的步骤
    Args:
        state: 当前执行状态

    Returns:
        首次的计划步骤
    """
    plan = await planner.ainvoke({"messages": [("user", state["input"])]})
    return {"plan": plan.steps}


async def replan_step(state: PlanExecute):
    """
    重新规划整个任务的步骤
    Args:
        state: 当前执行状态

    Returns:
        新的计划步骤
    """
    output = await replanner.ainvoke(state)
    if isinstance(output.action, Response):
        return {"response": output.action.response}
    else:
        return {"plan": output.action.steps}


def should_end(state: PlanExecute):
    if "response" in state and state["response"]:
        return END
    else:
        return "agent"


workflow = StateGraph(PlanExecute)
workflow.add_node("planner", plan_step)  # Add the plan node
workflow.add_node("agent", execute_step)  # Add the execution step
workflow.add_node("replan", replan_step)  # Add a replan node
workflow.add_edge(START, "planner")  # 从开始节点
workflow.add_edge("planner", "agent")  # From plan we go to agent
workflow.add_edge("agent", "replan")  # From agent, we replan

workflow.add_conditional_edges(
    "replan",
    # Next, we pass in the function that will determine which node is called next.
    should_end,
    ["agent", END],
)

# Finally, we compile it!
# This compiles it into a LangChain Runnable,
# meaning you can use it as you would any other runnable
app = workflow.compile()


async def main():
    config = {"recursion_limit": 50}
    inputs = {"input": "2024年澳网男子公开赛冠军的家乡是哪里？"}
    async for event in app.astream(inputs, config=config):
        for k, v in event.items():
            if k != "__end__":
                print(json.dumps(v, ensure_ascii=False))


if __name__ == '__main__':
    asyncio.run(main())
