import asyncio
from typing import Optional
from google.genai import types
from google.adk import Runner
from google.adk.agents import LlmAgent, Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.sessions import InMemorySessionService
from google.adk.tools.tool_context import ToolContext


def get_weather(city: str, tool_context: ToolContext) -> dict:
    """Retrieves the current weather report for a specified city.

    Args:
        city (str): The name of the city (e.g., "New York", "London", "Tokyo").

    Returns:
        dict: A dictionary containing the weather information.
              Includes a 'status' key ('success' or 'error').
              If 'success', includes a 'report' key with weather details.
              If 'error', includes an 'error_message' key.
    """
    print(f"--- Tool: get_weather_stateful called for {city} ---")
    preferred_unit = tool_context.state.get("user_preference_temperature_unit", "Celsius")  # Default to Celsius
    print(f"--- Tool: Reading state 'user_preference_temperature_unit': {preferred_unit} ---")

    city_normalized = city.lower().replace(" ", "")

    # Mock weather data (always stored in Celsius internally)
    mock_weather_db = {
        "newyork": {"temp_c": 25, "condition": "sunny"},
        "london": {"temp_c": 15, "condition": "cloudy"},
        "tokyo": {"temp_c": 18, "condition": "light rain"},
    }

    if city_normalized in mock_weather_db:
        data = mock_weather_db[city_normalized]
        temp_c = data["temp_c"]
        condition = data["condition"]

        if preferred_unit == "Fahrenheit":
            temp_value = (temp_c * 9 / 5) + 32
            temp_unit = "°F"
        else:
            temp_value = temp_c
            temp_unit = "°C"

        report = f"The weather in {city.capitalize()} is {condition} with a temperature of {temp_value:.0f}{temp_unit}."
        result = {"status": "success", "report": report}
        print(f"--- Tool: Generated report in {preferred_unit}. Result: {result} ---")

        # Example of writing back to state (optional for this tool)
        tool_context.state["last_city_checked_stateful"] = city
        print(f"--- Tool: Updated state 'last_city_checked_stateful': {city} ---")

        return result
    else:
        # Handle city not found
        error_msg = f"Sorry, I don't have weather information for '{city}'."
        print(f"--- Tool: City '{city}' not found. ---")
        return {"status": "error", "error_message": error_msg}


def say_hello(name: Optional[str] = None) -> str:
    """Provides a simple greeting. If a name is provided, it will be used.

    Args:
        name (str, optional): The name of the person to greet. Defaults to a generic greeting if not provided.

    Returns:
        str: A friendly greeting message.
    """
    if name:
        greeting = f"Hello, {name}!"
        print(f"--- Tool: say_hello called with name: {name} ---")
    else:
        greeting = "Hello there!"  # Default greeting if name is None or not explicitly passed
        print(f"--- Tool: say_hello called without a specific name (name_arg_value: {name}) ---")
    return greeting


def say_goodbye() -> str:
    """Provides a simple farewell message to conclude the conversation."""
    print(f"--- Tool: say_goodbye called ---")
    return "Goodbye! Have a great day."


async def call_agent_async(query: str, runner: Runner, user_id: str, session_id: str):
    """Sends a query to the agent and prints the final response."""
    print(f"\n>>> User Query: {query}")

    content = types.Content(role='user', parts=[types.Part(text=query)])

    final_response_text = ""

    async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
        print(f"llm response: {event.model_dump_json(indent=2, exclude_none=True)}")
        if event.is_final_response():
            if event.content and event.content.parts:
                final_response_text = event.content.parts[0].text
            elif event.actions and event.actions.escalate:  # Handle potential errors/escalations
                final_response_text = f"Agent escalated: {event.error_message or 'No specific message.'}"
            break

    print(f"<<< Agent Response: {final_response_text}")


# 创建llm实例
llm = LiteLlm(
    model="openai/deepseek-chat",
    base_url="https://api.deepseek.com/",
    api_key="sk-114cb5d9b3364649bd7ab553c3c06ea1",
)

# 创建agent实例
greeting_agent = Agent(
    model=llm,
    name="greeting_agent",
    instruction="You are the Greeting Agent. Your ONLY task is to provide a friendly greeting to the user. "
                "Use the 'say_hello' tool to generate the greeting. "
                "If the user provides their name, make sure to pass it to the tool. "
                "Do not engage in any other conversation or tasks.",
    description="Handles simple greetings and hellos using the 'say_hello' tool.",  # Crucial for delegation
    tools=[say_hello],
)
farewell_agent = Agent(
    model=llm,
    name="farewell_agent",
    instruction="You are the Farewell Agent. Your ONLY task is to provide a polite goodbye message. "
                "Use the 'say_goodbye' tool when the user indicates they are leaving or ending the conversation "
                "(e.g., using words like 'bye', 'goodbye', 'thanks bye', 'see you'). "
                "Do not perform any other actions.",
    description="Handles simple farewells and goodbyes using the 'say_goodbye' tool.",  # Crucial for delegation
    tools=[say_goodbye],
)

weather_agent_team = Agent(
    name="weather_agent_v2",
    model=llm,
    description="The main coordinator agent. Handles weather requests and delegates greetings/farewells to specialists.",
    instruction="You are the main Weather Agent coordinating a team. Your primary responsibility is to provide weather information. "
                "Use the 'get_weather' tool ONLY for specific weather requests (e.g., 'weather in London'). "
                "You have specialized sub-agents: "
                "1. 'greeting_agent': Handles simple greetings like 'Hi', 'Hello'. Delegate to it for these. "
                "2. 'farewell_agent': Handles simple farewells like 'Bye', 'See you'. Delegate to it for these. "
                "Analyze the user's query. If it's a greeting, delegate to 'greeting_agent'. If it's a farewell, delegate to 'farewell_agent'. "
                "If it's a weather request, handle it yourself using 'get_weather'. "
                "For anything else, respond appropriately or state you cannot handle it.",
    tools=[get_weather],
    sub_agents=[greeting_agent, farewell_agent]
)


async def run_team_conversation(query_list: list[str]):
    print("\n--- Testing Agent Team Delegation ---")
    session_service = InMemorySessionService()

    APP_NAME = "weather_tutorial_agent_team"
    USER_ID = "user_1_agent_team"
    SESSION_ID = "session_001_agent_team"
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID,
        state={"user_preference_temperature_unit": "Celsius"}
    )
    print(f"Session created: App='{APP_NAME}', User='{USER_ID}', Session='{SESSION_ID}'")

    runner_agent_team = Runner(  # Or use InMemoryRunner
        agent=weather_agent_team,
        app_name=APP_NAME,
        session_service=session_service
    )
    print(f"Runner created for agent '{weather_agent_team.name}'.")

    for query in query_list:
        await call_agent_async(query=query,
                               runner=runner_agent_team,
                               user_id=USER_ID,
                               session_id=SESSION_ID)


if __name__ == '__main__':
    asyncio.run(run_team_conversation(["Hello there!", "What is the weather in New York?", "Thanks, bye!"]))
