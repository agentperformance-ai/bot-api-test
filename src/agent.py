
import requests
import logging
import os
import aiohttp
import yaml
import json
from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    MetricsCollectedEvent,
    RoomInputOptions,
    WorkerOptions,
    cli,
    metrics,
)
from livekit.plugins import noise_cancellation, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from livekit.plugins import openai, deepgram

logger = logging.getLogger("agent")

load_dotenv(dotenv_path=".env.local")

auth_url = os.getenv("ABP_AUTH_URL")
tenancy_name = os.getenv("ABP_TENANCY_NAME")
username = os.getenv("ABP_USERNAME")
password = os.getenv("ABP_PASSWORD")
tenant_id = os.getenv("ABP_TENANT_ID")


class Assistant(Agent):
    def __init__(self, instructions: str = None) -> None:
        # Use provided instructions or default ones
        if instructions is None:
            instructions = """You are a helpful voice AI assistant. The user is interacting with you via voice, even if you perceive the conversation as text.
            You eagerly assist users with their questions by providing information from your extensive knowledge.
            Your responses are concise, to the point, and without any complex formatting or punctuation including emojis, asterisks, or other symbols.
            You are curious, friendly, and have a sense of humor."""
        
        super().__init__(instructions=instructions)

    # To add tools, use the @function_tool decorator.
    # Here's an example that adds a simple weather tool.
    # You also have to add `from livekit.agents import function_tool, RunContext` to the top of this file
    # @function_tool
    # async def lookup_weather(self, context: RunContext, location: str):
    #     """Use this tool to look up current weather information in the given location.
    #
    #     If the location is not supported by the weather service, the tool will indicate this. You must tell the user the location's weather is unavailable.
    #
    #     Args:
    #         location: The location to look up weather information for (e.g. city name)
    #     """
    #
    #     logger.info(f"Looking up weather for {location}")
    #
    #     return "sunny with a temperature of 70 degrees."

def generate_token(auth_url,username,password,tenant_id):
    url = f"{auth_url}/api/TokenAuth/Authenticate"
    print(("URL:", url))
    # url = "https://api-dev.insureplat.com/api/TokenAuth/Authenticate"

    headers = {
        "Content-Type": "application/json",
        "Abp.TenantId": tenant_id
    }

    payload = {
        "usernameOrEmailAddress": username,
        "password": password
    }

    # print(f"URL: {url}")
    # print(f"Headers: {headers}")
    # print(f"Payload: {payload}")

    response = requests.post(url, headers=headers, data=json.dumps(payload))

    # print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print("Authentication succeeded!")
        result=response.json()
        print(result['result']['accessToken'])
        return result['result']['accessToken']
    else:
        print("Authentication failed.")
    

async def fetch_instructions_from_api(api_url: str) -> str:
    """
    Fetch instructions from an API endpoint.
    
    Args:
        api_url: The API endpoint URL to fetch instructions from
        
    Returns:
        The instructions string from the API, or default instructions if API fails
    """
    default_instructions = """You are a helpful voice AI assistant. The user is interacting with you via voice, even if you perceive the conversation as text.
    You eagerly assist users with their questions by providing information from your extensive knowledge.
    Your responses are concise, to the point, and without any complex formatting or punctuation including emojis, asterisks, or other symbols.
    You are curious, friendly, and have a sense of humor."""
    token = generate_token(auth_url,username,password,tenant_id)  
    print("----------------------------------------------")
    print(token)
    print("----------------------------------------------")
    # Optional headers (depends on your API)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    # headers = {
    #     "Content-Type": "application/json",
    #     "Authorization": f"Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJodHRwOi8vc2NoZW1hcy54bWxzb2FwLm9yZy93cy8yMDA1LzA1L2lkZW50aXR5L2NsYWltcy9uYW1laWRlbnRpZmllciI6IjE1MTE3MCIsImh0dHA6Ly9zY2hlbWFzLnhtbHNvYXAub3JnL3dzLzIwMDUvMDUvaWRlbnRpdHkvY2xhaW1zL25hbWUiOiJtYW51QGdtYWlsLmNvbSIsImh0dHA6Ly9zY2hlbWFzLnhtbHNvYXAub3JnL3dzLzIwMDUvMDUvaWRlbnRpdHkvY2xhaW1zL2VtYWlsYWRkcmVzcyI6Im1hbnVAZ21haWwuY29tIiwiQXNwTmV0LklkZW50aXR5LlNlY3VyaXR5U3RhbXAiOiJaUFVXU0dGWDVVVVBOQ0hGTUFGWUo3VVFQSjNZNFgyNiIsImh0dHA6Ly9zY2hlbWFzLm1pY3Jvc29mdC5jb20vd3MvMjAwOC8wNi9pZGVudGl0eS9jbGFpbXMvcm9sZSI6WyJBZG1pbiIsIlByb3ZpZGVyIl0sImh0dHA6Ly93d3cuYXNwbmV0Ym9pbGVycGxhdGUuY29tL2lkZW50aXR5L2NsYWltcy90ZW5hbnRJZCI6IjEwNDI2Iiwic3ViIjoiMTUxMTcwIiwianRpIjoiYzZiOGEwNzQtMDU0Yy00ODA4LWJmNDAtYWQ0MDQ0N2Q5YTQ5IiwiaWF0IjoxNzYxMjk4NTM3LCJuYmYiOjE3NjEyOTg1MzcsImV4cCI6MTc2MTM4NDkzNywiaXNzIjoiSW5zdXJlcGxhdCIsImF1ZCI6Ikluc3VyZXBsYXQifQ.mhfb8_Tv08booElSalcONycFilhkXrPECnRuOEXQGE4"
    # }
    try:
        async with aiohttp.ClientSession() as session:
            # async with session.get(api_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
            async with session.post(api_url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    # data = await response.json()
                    # result = data.get("result", {})
                    
                    result = await response.text()
                    # data = json.loads(result)

                    # # Step 2: Extract the YAML string from "message"
                    # yaml_text = data.get("message", "")

                    # # Step 3: Parse YAML text
                    # parsed = yaml.safe_load(yaml_text)

                    # # Step 4: Access botflow
                    # botflow = parsed.get("botflow")
                    print("----------------------------------------------------------------------")
                    logger.info(f"API results: {result}")
                    print("----------------------------------------------------------------------")
                    
                    # Extract instructions from the API response
                    # Adjust this based on your actual API response structure
                    # lead_meta = result.get("leadProfileMetadata") or {}
                    # logger.info(f"Lead metadata: {lead_meta}")
                    
                    # api_instructions = result.get("botflow")
                    # print("--------------------------------------------------------")
                    # logger.info(f"API Instructions: {api_instructions}")
                    # print("--------------------------------------------------------")

                    # Get prompt or instructions from the result
                    # instructions = result.get("prompt") or lead_meta.get("instructions") or ""
                    instructions = result or ""
                    print("--------------------------------------------------------")
                    logger.info(f"Instructions: {instructions}")
                    print("--------------------------------------------------------")
                    

                    if instructions:
                        logger.info(f"Successfully fetched instructions from API: {api_url}")
                        return instructions
                    else:
                        logger.warning("API response did not contain instructions, using default")
                        return default_instructions
                else:
                    logger.error(f"API returned status {response.status}, using default instructions")
                    return default_instructions
    except aiohttp.ClientError as e:
        logger.error(f"Failed to fetch instructions from API: {e}, using default instructions")
        return default_instructions
    except Exception as e:
        logger.error(f"Unexpected error fetching instructions: {e}, using default instructions")
        return default_instructions


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    # Logging setup
    # Add any other context you want in all log entries here
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # Set up a voice AI pipeline using OpenAI, Cartesia, AssemblyAI, and the LiveKit turn detector
    session = AgentSession(
        stt=deepgram.STT(model="nova-3",mip_opt_out=True),
        llm=openai.LLM(model="gpt-4o-mini", service_tier = "priority"),
        tts=deepgram.TTS(
        model="aura-asteria-en",
        ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"], 
        preemptive_generation=True,
    )

    # To use a realtime model instead of a voice pipeline, use the following session setup instead.
    # (Note: This is for the OpenAI Realtime API. For other providers, see https://docs.livekit.io/agents/models/realtime/))
    # 1. Install livekit-agents[openai]
    # 2. Set OPENAI_API_KEY in .env.local
    # 3. Add `from livekit.plugins import openai` to the top of this file
    # 4. Use the following session setup instead of the version above
    # session = AgentSession(
    #     llm=openai.realtime.RealtimeModel(voice="marin")
    # )

    # Metrics collection, to measure pipeline performance
    # For more information, see https://docs.livekit.io/agents/build/metrics/
    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Usage: {summary}")

    ctx.add_shutdown_callback(log_usage)

    # # Add a virtual avatar to the session, if desired
    # # For other providers, see https://docs.livekit.io/agents/models/avatar/
    # avatar = hedra.AvatarSession(
    #   avatar_id="...",  # See https://docs.livekit.io/agents/models/avatar/plugins/hedra
    # )
    # # Start the avatar and wait for it to join
    # await avatar.start(session, room=ctx.room)

    # Fetch instructions from API
    # api_url = os.getenv('INSTRUCTIONS_API_URL', 'http://api-dev.insureplat.com/api/services/app/Bot/flattenBot?botId=202&version=6')
    api_url = os.getenv('FLATTEN_BOT_URL')
    instructions = await fetch_instructions_from_api(api_url)
    # print("----------------------------------------------------")
    # logger.info(f"instructions: {instructions}")
    # print("----------------------------------------------------")
    # Start the session, which initializes the voice pipeline and warms up the models
    await session.start(
        agent=Assistant(instructions=instructions),
        room=ctx.room,
        room_input_options=RoomInputOptions(
            # For telephony applications, use `BVCTelephony` for best results
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    # Join the room and connect to the user
    await ctx.connect()



if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))

# ----------------------------------------------------------------------------------------------

