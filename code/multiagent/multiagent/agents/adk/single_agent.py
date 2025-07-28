import asyncio
from typing import Optional, Dict, Any
from google.genai import types
from google.adk import Runner
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.sessions import InMemorySessionService
from google.adk.tools.tool_context import ToolContext
from google.adk.tools.base_tool import BaseTool
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse


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


def block_keyword_guardrail(
        callback_context: CallbackContext, llm_request: LlmRequest
) -> Optional[LlmResponse]:
    """
    Inspects the latest user message for 'BLOCK'. If found, blocks the LLM call
    and returns a predefined LlmResponse. Otherwise, returns None to proceed.
    """
    agent_name = callback_context.agent_name  # Get the name of the agent whose model call is being intercepted
    print(f"--- Callback: block_keyword_guardrail running for agent: {agent_name} ---")

    # Extract the text from the latest user message in the request history
    last_user_message_text = ""
    if llm_request.contents:
        # Find the most recent message with role 'user'
        for content in reversed(llm_request.contents):
            if content.role == 'user' and content.parts:
                # Assuming text is in the first part for simplicity
                if content.parts[0].text:
                    last_user_message_text = content.parts[0].text
                    break  # Found the last user message text

    print(f"--- Callback: Inspecting last user message: '{last_user_message_text[:100]}...' ---")  # Log first 100 chars

    # --- Guardrail Logic ---
    keyword_to_block = "BLOCK"
    if keyword_to_block in last_user_message_text.upper():  # Case-insensitive check
        print(f"--- Callback: Found '{keyword_to_block}'. Blocking LLM call! ---")
        # Optionally, set a flag in state to record the block event
        callback_context.state["guardrail_block_keyword_triggered"] = True
        print(f"--- Callback: Set state 'guardrail_block_keyword_triggered': True ---")

        # Construct and return an LlmResponse to stop the flow and send this back instead
        return LlmResponse(
            content=types.Content(
                role="model",  # Mimic a response from the agent's perspective
                parts=[
                    types.Part(
                        text=f"I cannot process this request because it contains the blocked keyword '{keyword_to_block}'."
                    )
                ],
            )
            # Note: You could also set an error_message field here if needed
        )
    else:
        # Keyword not found, allow the request to proceed to the LLM
        print(f"--- Callback: Keyword not found. Allowing LLM call for {agent_name}. ---")
        return None  # Returning None signals ADK to continue normally


def block_paris_tool_guardrail(
        tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext
) -> Optional[Dict]:
    """
    Checks if 'get_weather_stateful' is called for 'Paris'.
    If so, blocks the tool execution and returns a specific error dictionary.
    Otherwise, allows the tool call to proceed by returning None.
    """
    tool_name = tool.name
    agent_name = tool_context.agent_name  # Agent attempting the tool call
    print(f"--- Callback: block_paris_tool_guardrail running for tool '{tool_name}' in agent '{agent_name}' ---")
    print(f"--- Callback: Inspecting args: {args} ---")

    # --- Guardrail Logic ---
    target_tool_name = "get_weather"  # Match the function name used by FunctionTool
    blocked_city = "paris"

    # Check if it's the correct tool and the city argument matches the blocked city
    if tool_name == target_tool_name:
        city_argument = args.get("city", "")  # Safely get the 'city' argument
        if city_argument and city_argument.lower() == blocked_city:
            print(f"--- Callback: Detected blocked city '{city_argument}'. Blocking tool execution! ---")
            # Optionally update state
            tool_context.state["guardrail_tool_block_triggered"] = True
            print(f"--- Callback: Set state 'guardrail_tool_block_triggered': True ---")

            # Return a dictionary matching the tool's expected output format for errors
            # This dictionary becomes the tool's result, skipping the actual tool run.
            return {
                "status": "error",
                "error_message": f"Policy restriction: Weather checks for '{city_argument.capitalize()}' are currently disabled by a tool guardrail."
            }
        else:
            print(f"--- Callback: City '{city_argument}' is allowed for tool '{tool_name}'. ---")
    else:
        print(f"--- Callback: Tool '{tool_name}' is not the target tool. Allowing. ---")

    # If the checks above didn't return a dictionary, allow the tool to execute
    print(f"--- Callback: Allowing tool '{tool_name}' to proceed. ---")
    return None  # Returning None allows the actual tool function to run


async def run_conversation():
    # 创建llm实例
    llm = LiteLlm(
        model="openai/deepseek-chat",
        base_url="https://api.deepseek.com/",
        api_key="sk-114cb5d9b3364649bd7ab553c3c06ea1",
        stream=True
    )
    # 创建agent实例
    weather_agent = LlmAgent(
        name="weather_agent_v1",
        model=llm,
        description="Provides weather information for specific cities.",
        instruction="You are a helpful weather assistant. "
                    "When the user asks for the weather in a specific city, "
                    "use the 'get_weather' tool to find the information. "
                    "If the tool returns an error, inform the user politely. "
                    "If the tool is successful, present the weather report clearly.",
        tools=[get_weather],
        before_model_callback=block_keyword_guardrail,
        before_tool_callback=block_paris_tool_guardrail
    )

    session_service = InMemorySessionService()
    app_name = "weather_app"
    user_id = "user_1"
    session_id = "session_1"

    # Create the specific session where the conversation will happen
    session = await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id
    )
    print(f"Session created: App='{app_name}', User='{user_id}', Session='{session_id}'")

    runner = Runner(
        agent=weather_agent,
        app_name=app_name,
        session_service=session_service
    )
    print(f"Runner created for agent '{runner.agent.name}'.")

    await call_agent_async("What is the weather like in London?", runner, user_id, session_id)

    stored_session = session_service.sessions[app_name][user_id][session_id]

    print(f"Final Last City Checked (by tool): {stored_session.state.get('last_city_checked_stateful', 'Not Set')}")

    # # 修改session当中的信息
    # stored_session.state["user_preference_temperature_unit"] = "Fahrenheit"
    #
    # await call_agent_async(query="Hi!",
    #                        runner=runner,
    #                        user_id=user_id,
    #                        session_id=session_id)
    #
    # print(f"Final Last City Checked (by tool): {stored_session.state.get('last_city_checked_stateful', 'Not Set')}")
    #
    # await call_agent_async(query="Tell me the weather in New York.",
    #                        runner=runner,
    #                        user_id=user_id,
    #                        session_id=session_id)
    #
    # print(f"Final Last City Checked (by tool): {stored_session.state.get('last_city_checked_stateful', 'Not Set')}")


if __name__ == '__main__':
    asyncio.run(run_conversation())
