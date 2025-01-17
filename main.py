import asyncio
import os
from aiohttp import ClientSession
from dotenv import load_dotenv
from datetime import datetime
from zoneinfo import ZoneInfo

# Load environment variables from .env file
load_dotenv()

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.pipeline.runner import PipelineRunner
from pipecat.transports.services.daily import DailyParams, DailyTransport
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.openai import OpenAILLMService
from pipecat.services.deepgram import DeepgramSTTService, DeepgramTTSService
from pipecat_flows import FlowManager, FlowArgs, FlowConfig, FlowResult
from runner import configure
from calcom_api import CalComAPI, BookingDetails

# Initialize Cal.com API
calcom_api = CalComAPI()


async def handle_booking_request(args: FlowArgs) -> FlowResult:
    """Handle the booking request with a fixed date."""
    # Fixed date: January 19, 2025 at 12:00 PM UTC
    booking_time = datetime(2025, 1, 19, 12, 0, tzinfo=ZoneInfo("UTC")).isoformat()

    # Get the collected information from previous nodes
    name = "Roger Rabbit"
    company = "Who Framed Co."

    booking_details: BookingDetails = {
        "name": name,
        "email": "test@example.com",  # You might want to collect this in a previous node
        "company": company,
        "phone": "123-456-7890",  # You might want to collect this in a previous node
        "timezone": "UTC",
        "startTime": booking_time,
        "notes": "Booking from AI Lead Qualifier",
    }

    booking_response = await calcom_api.create_booking(booking_details)

    if booking_response["success"]:
        return FlowResult(
            status="success",
            message="Great! I've booked an appointment for you on January 19, 2025 at 12:00 PM UTC.",
            data=booking_response["booking"],
        )
    else:
        return FlowResult(
            status="error",
            message="I apologize, but I couldn't book the appointment. "
            + booking_response.get("error", ""),
            data=None,
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
                        "parameters": {"type": "object", "properties": {}},
                        "transition_to": "offer_call_option",
                    },
                },
            ],
        },
        # "identify_use_case": {
        #     "task_messages": [
        #         {
        #             "role": "system",
        #             "content": "Ask about their voice AI needs.",
        #         }
        #     ],
        #     "functions": [
        #         {
        #             "type": "function",
        #             "function": {
        #                 "name": "identify_use_case",
        #                 "description": "Record their use case needs",
        #                 "parameters": {"type": "object", "properties": {}},
        #                 "transition_to": "establish_timescales",
        #             },
        #         },
        #     ],
        # },
        # "establish_timescales": {
        #     "task_messages": [
        #         {
        #             "role": "system",
        #             "content": "Ask about their desired timeline. Ask for both start date and deadline.",
        #         }
        #     ],
        #     "functions": [
        #         {
        #             "type": "function",
        #             "function": {
        #                 "name": "establish_timescales",
        #                 "description": "Record project timeline",
        #                 "parameters": {"type": "object", "properties": {}},
        #                 "transition_to": "determine_budget",
        #             },
        #         },
        #     ],
        # },
        # "determine_budget": {
        #     "task_messages": [
        #         {
        #             "role": "system",
        #             "content": "Ask about their budget for the voice AI solution. If they're unsure, explain our tiered options.",
        #         }
        #     ],
        #     "functions": [
        #         {
        #             "type": "function",
        #             "function": {
        #                 "name": "determine_budget",
        #                 "description": "Record their budget range",
        #                 "parameters": {"type": "object", "properties": {}},
        #                 "transition_to": "assess_feedback",
        #             },
        #         },
        #     ],
        # },
        # "assess_feedback": {
        #     "task_messages": [
        #         {
        #             "role": "system",
        #             "content": "Ask for their feedback on this AI interaction experience.",
        #         }
        #     ],
        #     "functions": [
        #         {
        #             "type": "function",
        #             "function": {
        #                 "name": "assess_feedback",
        #                 "description": "Record their interaction feedback",
        #                 "parameters": {"type": "object", "properties": {}},
        #                 "transition_to": "offer_call_option",
        #             },
        #         },
        #     ],
        # },
        "offer_call_option": {
            "task_messages": [
                {
                    "role": "system",
                    "content": "Ask if they would like to book an appointment for January 19, 2025 at 12:00 PM UTC with John George.",
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "handle_booking_request",
                        "description": "Handle the booking request",
                        "handler": handle_booking_request,
                        "parameters": {"type": "object", "properties": {}},
                        "transition_to": "close_call",
                    },
                },
            ],
        },
        "close_call": {
            "task_messages": [
                {
                    "role": "system",
                    "content": "Thank them for their time and end the conversation warmly.",
                }
            ],
            "functions": [],
            "post_actions": [{"type": "end_conversation"}],
        },
    },
}


# Main function
async def main():
    """Setup and run the lead qualification agent."""
    async with ClientSession() as session:
        # Get room configuration from runner
        (room_url, _) = await configure(session)

        # Initialize services
        transport = DailyTransport(
            room_url,
            None,
            "Lead Qualification Bot",
            DailyParams(
                audio_out_enabled=True,
                vad_enabled=True,
                vad_analyzer=SileroVADAnalyzer(),
                vad_audio_passthrough=True,
            ),
        )

        stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"))
        tts = DeepgramTTSService(
            api_key=os.getenv("DEEPGRAM_API_KEY"), voice="aura-helios-en"
        )
        llm = OpenAILLMService(api_key=os.getenv("OPENAI_API_KEY"), model="gpt-4o")

        context = OpenAILLMContext()
        context_aggregator = llm.create_context_aggregator(context)

        # Create pipeline
        pipeline = Pipeline(
            [
                transport.input(),
                stt,
                context_aggregator.user(),
                llm,
                tts,
                transport.output(),
                context_aggregator.assistant(),
            ]
        )

        task = PipelineTask(pipeline, PipelineParams(allow_interruptions=True))

        # Initialize flow manager
        flow_manager = FlowManager(task=task, llm=llm, tts=tts, flow_config=flow_config)

        @transport.event_handler("on_first_participant_joined")
        async def on_first_participant_joined(transport, participant):
            await transport.capture_participant_transcription(participant["id"])
            await flow_manager.initialize()
            await task.queue_frames([context_aggregator.user().get_context_frame()])

        runner = PipelineRunner()
        await runner.run(task)


if __name__ == "__main__":
    asyncio.run(main())
