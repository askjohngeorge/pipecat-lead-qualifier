import asyncio
import os
from aiohttp import ClientSession
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.pipeline.runner import PipelineRunner
from pipecat.transports.services.daily import DailyParams, DailyTransport
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.openai import OpenAILLMService
from pipecat.services.deepgram import DeepgramSTTService, DeepgramTTSService
from pipecat_flows import FlowManager, FlowArgs, FlowConfig, FlowResult


# Define result types
class NameResult(FlowResult):
    name: str


class UseCaseResult(FlowResult):
    use_case: str


class TimescaleResult(FlowResult):
    start_date: str
    deadline: str


class BudgetResult(FlowResult):
    budget: str


class FeedbackResult(FlowResult):
    feedback: str


class CallOptionResult(FlowResult):
    option: str  # "book" or "contact"


# Define handlers
async def collect_name(args: FlowArgs) -> NameResult:
    """Collect caller's name."""
    name = args["name"]
    return {"name": name}


async def identify_use_case(args: FlowArgs) -> UseCaseResult:
    """Identify specific use case."""
    use_case = args["use_case"]
    return {"use_case": use_case}


async def establish_timescales(args: FlowArgs) -> TimescaleResult:
    """Establish project timescales."""
    return {"start_date": args["start_date"], "deadline": args["deadline"]}


async def determine_budget(args: FlowArgs) -> BudgetResult:
    """Determine budget range."""
    return {"budget": args["budget"]}


async def assess_feedback(args: FlowArgs) -> FeedbackResult:
    """Assess AI interaction experience."""
    return {"feedback": args["feedback"]}


async def offer_call_option(args: FlowArgs) -> CallOptionResult:
    """Offer discovery call options."""
    return {"option": args["option"]}


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
                    "content": "Greet the caller warmly and ask for their name. Wait for them to provide their name before using collect_name.",
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "collect_name",
                        "handler": collect_name,
                        "description": "Record the caller's name",
                        "parameters": {
                            "type": "object",
                            "properties": {"name": {"type": "string"}},
                            "required": ["name"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "proceed_to_use_case",
                        "description": "Move to use case discussion",
                        "parameters": {"type": "object", "properties": {}},
                        "transition_to": "identify_use_case",
                    },
                },
            ],
        },
        "identify_use_case": {
            "task_messages": [
                {
                    "role": "system",
                    "content": "Ask about their voice AI needs. Wait for their response, then use identify_use_case to record it.",
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "identify_use_case",
                        "handler": identify_use_case,
                        "description": "Record their use case needs",
                        "parameters": {
                            "type": "object",
                            "properties": {"use_case": {"type": "string"}},
                            "required": ["use_case"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "proceed_to_timescales",
                        "description": "Move to timeline discussion",
                        "parameters": {"type": "object", "properties": {}},
                        "transition_to": "establish_timescales",
                    },
                },
            ],
        },
        "establish_timescales": {
            "task_messages": [
                {
                    "role": "system",
                    "content": "Ask about their desired timeline. Ask for both start date and deadline before using establish_timescales.",
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "establish_timescales",
                        "handler": establish_timescales,
                        "description": "Record project timeline",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "start_date": {"type": "string"},
                                "deadline": {"type": "string"},
                            },
                            "required": ["start_date", "deadline"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "proceed_to_budget",
                        "description": "Move to budget discussion",
                        "parameters": {"type": "object", "properties": {}},
                        "transition_to": "determine_budget",
                    },
                },
            ],
        },
        "determine_budget": {
            "task_messages": [
                {
                    "role": "system",
                    "content": "Ask about their budget for the voice AI solution. If they're unsure, explain our tiered options.",
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "determine_budget",
                        "handler": determine_budget,
                        "description": "Record their budget range",
                        "parameters": {
                            "type": "object",
                            "properties": {"budget": {"type": "string"}},
                            "required": ["budget"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "proceed_to_feedback",
                        "description": "Move to feedback collection",
                        "parameters": {"type": "object", "properties": {}},
                        "transition_to": "assess_feedback",
                    },
                },
            ],
        },
        "assess_feedback": {
            "task_messages": [
                {
                    "role": "system",
                    "content": "Ask for their feedback on this AI interaction experience.",
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "assess_feedback",
                        "handler": assess_feedback,
                        "description": "Record their interaction feedback",
                        "parameters": {
                            "type": "object",
                            "properties": {"feedback": {"type": "string"}},
                            "required": ["feedback"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "proceed_to_call_options",
                        "description": "Move to call booking options",
                        "parameters": {"type": "object", "properties": {}},
                        "transition_to": "offer_call_option",
                    },
                },
            ],
        },
        "offer_call_option": {
            "task_messages": [
                {
                    "role": "system",
                    "content": "Offer them the choice between booking a video call with John George or receiving follow-up via email.",
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "offer_call_option",
                        "handler": offer_call_option,
                        "description": "Record their preferred follow-up method",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "option": {
                                    "type": "string",
                                    "enum": ["book", "contact"],
                                }
                            },
                            "required": ["option"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "proceed_to_close",
                        "description": "Move to call closing",
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
        # Load configurations from environment variables
        DAILY_ROOM_URL = os.getenv("DAILY_ROOM_URL")
        OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

        # Initialize transport
        transport = DailyTransport(
            room_url=DAILY_ROOM_URL,
            token=None,
            bot_name="Lead Qualification Bot",
            params=DailyParams(
                audio_out_enabled=True,
                vad_enabled=True,
            ),
        )

        # Initialize services
        stt = DeepgramSTTService(api_key=DEEPGRAM_API_KEY)
        tts = DeepgramTTSService(api_key=DEEPGRAM_API_KEY, voice="aura-helios-en")
        llm = OpenAILLMService(api_key=OPENAI_API_KEY, model="gpt-4o")

        # Create a context aggregator
        context = OpenAILLMContext()
        context_aggregator = llm.create_context_aggregator(context)

        # Build the processing pipeline
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

        # Create a task for the pipeline
        task = PipelineTask(
            pipeline=pipeline, params=PipelineParams(allow_interruptions=True)
        )

        # Initialize the flow manager
        flow_manager = FlowManager(
            task=task,
            llm=llm,
            tts=tts,
            flow_config=flow_config,  # Using the flow configuration defined earlier
        )

        @transport.event_handler("on_first_participant_joined")
        async def on_first_participant_joined(transport, participant):
            """Start the flow when the first participant joins."""
            await transport.capture_participant_transcription(participant["id"])
            await flow_manager.initialize()  # Initialize the flow manager
            await task.queue_frames(
                [context_aggregator.user().get_context_frame()]
            )  # Kick off flow

        # Run the pipeline
        runner = PipelineRunner()
        await runner.run(task)


# Run the asyncio event loop
if __name__ == "__main__":
    asyncio.run(main())
