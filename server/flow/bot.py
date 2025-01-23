import asyncio
import sys
import signal
import argparse
from pathlib import Path
from aiohttp import ClientSession
from dotenv import load_dotenv

from utils.calcom_api import CalComAPI, BookingDetails
from utils.config import AppConfig
from utils.transports import TransportFactory
from utils.pipelines import PipelineBuilder

# Load environment variables from .env file
load_dotenv()

# Initialize configuration
config = AppConfig()

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.pipeline.runner import PipelineRunner
from pipecat.transports.services.daily import DailyParams, DailyTransport
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.openai import OpenAILLMService
from pipecat.services.deepgram import DeepgramSTTService, DeepgramTTSService
from pipecat_flows import FlowManager, FlowArgs, FlowConfig, FlowResult
from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIProcessor

# Initialize Cal.com API
calcom_api = CalComAPI()


async def handle_availability_check(args: FlowArgs) -> FlowResult:
    """Check availability and present options to the user."""
    availability = await calcom_api.get_availability(days=7)

    if not availability["success"]:
        # First attempt failed, try again
        availability = await calcom_api.get_availability(days=7)
        if not availability["success"]:
            return FlowResult(
                status="error",
                message="I sincerely apologize, but we're experiencing some technical difficulties with our scheduling system. Would it be alright if I had our scheduling team call you back within the next hour to set up the demo? They can be reached directly at our scheduling line if you prefer: 555-0123.",
                data={"availability_check_failed": True},
            )

    # Get the first two available dates
    formatted = calcom_api._last_availability_check
    if not formatted or not formatted["dates"]:
        return FlowResult(
            status="error",
            message="I apologize, but I'm not seeing any available slots in the next 7 days. Would it be alright if I had our scheduling team call you to find a time that works for you?",
            data={"no_availability": True},
        )

    # Take the first two available dates
    available_dates = formatted["dates"][:2]
    date_options = " or ".join(available_dates)

    return FlowResult(
        status="success",
        message=f"I see we have availability on {date_options}. Which day would work better for you?",
        data={"available_dates": available_dates},
    )


async def handle_time_slot_selection(args: FlowArgs) -> FlowResult:
    """Present time slots for the selected date."""
    selected_date = args.get("selected_date")

    if not selected_date:
        return FlowResult(
            status="error",
            message="I apologize, but I didn't catch which date you preferred. Could you please let me know if you'd prefer {available_dates}?",
            data={"missing_date": True},
        )

    morning_slot, afternoon_slot = calcom_api.get_morning_afternoon_slots(selected_date)

    if not morning_slot and not afternoon_slot:
        return FlowResult(
            status="error",
            message="I apologize, but it seems those time slots are no longer available. Let me check availability again.",
            data={"retry_availability": True},
        )

    time_options = []
    if morning_slot:
        time_options.append(morning_slot["time"])
    if afternoon_slot:
        time_options.append(afternoon_slot["time"])

    time_options_str = " or ".join(time_options)
    return FlowResult(
        status="success",
        message=f"Great. On {selected_date}, I have slots at {time_options_str}. Which would you prefer?",
        data={"morning_slot": morning_slot, "afternoon_slot": afternoon_slot},
    )


async def handle_booking_confirmation(args: FlowArgs) -> FlowResult:
    """Attempt to book the selected time slot."""
    selected_slot = args.get("selected_slot")

    if not selected_slot:
        return FlowResult(
            status="error",
            message="I apologize, but I didn't catch which time slot you preferred. Could you please let me know which time works better for you?",
            data={"missing_time": True},
        )

    booking_details: BookingDetails = {
        "name": args.get("name", "Unknown"),
        "email": "test@example.com",  # In production, get from args
        "company": args.get("company", "Unknown"),
        "phone": "123-456-7890",  # In production, get from args
        "timezone": "UTC",
        "startTime": selected_slot["datetime"],
        "notes": "Booking from AI Lead Qualifier",
    }

    # First booking attempt
    booking = await calcom_api.create_booking(booking_details)
    if not booking["success"]:
        # Second booking attempt
        booking = await calcom_api.create_booking(booking_details)
        if not booking["success"]:
            return FlowResult(
                status="error",
                message="I sincerely apologize, but our booking system seems to be having issues right now. To make sure you get this time slot, I can have our scheduling team call you back within the next 30 minutes to confirm it. Alternatively, you can book directly through our scheduling line at 555-0123. Which would you prefer?",
                data={"booking_failed": True},
            )

    return FlowResult(
        status="success",
        message=f"Excellent! I've confirmed your demo for {selected_slot['date']} at {selected_slot['time']}. You'll receive a calendar invitation shortly with all the details. Is there anything else you'd like to know about the demo?",
        data={"booking": booking["booking"]},
    )


# Define the flow configuration
flow_config: FlowConfig = {
    "initial_node": "rapport_building",
    "nodes": {
        "rapport_building": {
            "role_messages": [
                {
                    "role": "system",
                    "content": "You are a lead qualification agent. Your responses will be converted to audio. Keep responses natural and friendly.",
                }
            ],
            "task_messages": [
                {
                    "role": "system",
                    "content": "Greet the caller warmly and ask for their name.",
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "collect_name",
                        "description": "Record the caller's name",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "The caller's name",
                                }
                            },
                            "required": ["name"],
                        },
                        "transition_to": "check_availability",
                    },
                },
            ],
        },
        "check_availability": {
            "task_messages": [
                {
                    "role": "system",
                    "content": "Use assumptive closing technique to naturally transition to booking a demo. Say something like 'Let's get you set up with a quick demo so you can see firsthand how this will help your business. Let me check our calendar...'",
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "handle_availability_check",
                        "description": "Check calendar availability",
                        "handler": handle_availability_check,
                        "parameters": {"type": "object", "properties": {}},
                        "transition_to": "present_time_slots",
                    },
                },
            ],
        },
        "present_time_slots": {
            "task_messages": [
                {
                    "role": "system",
                    "content": "Based on the user's date preference, present available time slots. If they haven't chosen a date yet, ask them to choose from the available dates first.",
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "handle_time_slot_selection",
                        "description": "Present time slots for selected date",
                        "handler": handle_time_slot_selection,
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "selected_date": {
                                    "type": "string",
                                    "description": "The date selected by the user",
                                }
                            },
                            "required": ["selected_date"],
                        },
                        "transition_to": "confirm_booking",
                    },
                },
            ],
        },
        "confirm_booking": {
            "task_messages": [
                {
                    "role": "system",
                    "content": "Attempt to book the selected time slot. If successful, confirm the booking enthusiastically. If it fails, handle gracefully with alternative booking options.",
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "handle_booking_confirmation",
                        "description": "Confirm and create the booking",
                        "handler": handle_booking_confirmation,
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "selected_slot": {
                                    "type": "object",
                                    "description": "The time slot selected by the user",
                                    "properties": {
                                        "date": {"type": "string"},
                                        "time": {"type": "string"},
                                        "datetime": {"type": "string"},
                                        "is_morning": {"type": "boolean"},
                                    },
                                    "required": ["date", "time", "datetime"],
                                }
                            },
                            "required": ["selected_slot"],
                        },
                        "transition_to": "close_call",
                    },
                },
            ],
        },
        "close_call": {
            "task_messages": [
                {
                    "role": "system",
                    "content": "Thank them warmly and end the conversation professionally. If there were any booking issues, make sure to clearly state the next steps.",
                }
            ],
            "functions": [],
            "post_actions": [{"type": "end_conversation"}],
        },
    },
}


async def cleanup(runner, transport, task):
    """Cleanup function to handle graceful shutdown."""
    await runner.stop_when_done()
    await task.stop_when_done()
    if transport:
        await transport.leave()


async def main():
    """Setup and run the lead qualification agent."""
    parser = argparse.ArgumentParser(description="Lead Qualification Bot")
    parser.add_argument(
        "-u", "--url", type=str, required=True, help="URL of the Daily room to join"
    )
    parser.add_argument(
        "-t", "--token", type=str, required=True, help="Token for the Daily room"
    )
    args = parser.parse_args()

    if not args.url or not args.token:
        print("Error: Both --url and --token are required")
        sys.exit(1)

    # Initialize services
    stt = DeepgramSTTService(api_key=config.deepgram_api_key)
    tts = DeepgramTTSService(api_key=config.deepgram_api_key)
    llm = OpenAILLMService(api_key=config.openai_api_key)

    # Initialize transport using factory
    transport_factory = TransportFactory(config)
    transport = transport_factory.create_lead_qualifier_transport(args.url, args.token)

    # Initialize RTVI
    rtvi_config = RTVIConfig(config=[])
    rtvi = RTVIProcessor(config=rtvi_config)

    # Initialize context with initial messages
    initial_messages = flow_config["nodes"]["rapport_building"]["role_messages"]
    context = OpenAILLMContext(messages=initial_messages)

    # Build pipeline using builder
    pipeline_builder = PipelineBuilder(transport, stt, tts, llm, context=context)
    pipeline = pipeline_builder.add_rtvi(rtvi).build()

    task = PipelineTask(
        pipeline,
        PipelineParams(
            allow_interruptions=True,
            enable_metrics=True,
            enable_usage_metrics=True,
            observers=[rtvi.observer()],
        ),
    )

    # Initialize flow manager
    flow_manager = FlowManager(
        task=task,
        llm=llm,
        context_aggregator=pipeline_builder.context_aggregator,
        tts=tts,
        flow_config=flow_config,
    )

    @rtvi.event_handler("on_client_ready")
    async def on_client_ready(rtvi):
        await rtvi.set_bot_ready()

    @transport.event_handler("on_first_participant_joined")
    async def on_first_participant_joined(transport, participant):
        await transport.capture_participant_transcription(participant["id"])
        await flow_manager.initialize()
        # No need to queue additional context frames here since the flow manager will handle it

    @transport.event_handler("on_participant_left")
    async def on_participant_left(transport, participant, reason):
        await runner.stop_when_done()

    # Set up signal handlers for graceful shutdown
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(
            sig, lambda: asyncio.create_task(cleanup(runner, transport, task))
        )

    try:
        runner = PipelineRunner()
        await runner.run(task)
    except asyncio.CancelledError:
        await cleanup(runner, transport, task)
    finally:
        # Remove signal handlers
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.remove_signal_handler(sig)


if __name__ == "__main__":
    asyncio.run(main())
