import asyncio
from aiohttp import ClientSession
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
            "task_messages": [
                {
                    "role": "system",
                    "content": (
                        "Greet the caller warmly and establish their name. "
                        "Ask: 'How can I help you?' and 'May I know your full name?' "
                        "Proceed to identify_use_case after collecting their name."
                    ),
                }
            ],
            "functions": [
                {
                    "name": "collect_name",
                    "handler": collect_name,
                    "description": "Collect caller's name",
                    "input_schema": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                        "required": ["name"],
                    },
                    "transition_to": "identify_use_case",
                }
            ],
        },
        "identify_use_case": {
            "task_messages": [
                {
                    "role": "system",
                    "content": (
                        "Ask the caller about their needs for a voice AI solution. "
                        "E.g., 'What kind of voice AI solution are you looking for?' "
                        "Refine their answer to a specific use case."
                    ),
                }
            ],
            "functions": [
                {
                    "name": "identify_use_case",
                    "handler": identify_use_case,
                    "description": "Identify specific use case",
                    "input_schema": {
                        "type": "object",
                        "properties": {"use_case": {"type": "string"}},
                        "required": ["use_case"],
                    },
                    "transition_to": "establish_timescales",
                }
            ],
        },
        "establish_timescales": {
            "task_messages": [
                {
                    "role": "system",
                    "content": (
                        "Ask the caller about their desired start date and deadline. "
                        "E.g., 'When are you hoping to implement this solution?' "
                        "and 'Do you have a target deadline?'"
                    ),
                }
            ],
            "functions": [
                {
                    "name": "establish_timescales",
                    "handler": establish_timescales,
                    "description": "Establish project timescales",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "start_date": {"type": "string"},
                            "deadline": {"type": "string"},
                        },
                        "required": ["start_date", "deadline"],
                    },
                    "transition_to": "determine_budget",
                }
            ],
        },
        "determine_budget": {
            "task_messages": [
                {
                    "role": "system",
                    "content": (
                        "Ask about the budget for the voice AI solution. "
                        "Provide tiered options if they are unsure."
                    ),
                }
            ],
            "functions": [
                {
                    "name": "determine_budget",
                    "handler": determine_budget,
                    "description": "Determine budget range",
                    "input_schema": {
                        "type": "object",
                        "properties": {"budget": {"type": "string"}},
                        "required": ["budget"],
                    },
                    "transition_to": "assess_feedback",
                }
            ],
        },
        "assess_feedback": {
            "task_messages": [
                {
                    "role": "system",
                    "content": (
                        "Ask about their experience with the conversation so far. "
                        "E.g., 'How do you feel about the quality of this interaction?'"
                    ),
                }
            ],
            "functions": [
                {
                    "name": "assess_feedback",
                    "handler": assess_feedback,
                    "description": "Assess AI interaction experience",
                    "input_schema": {
                        "type": "object",
                        "properties": {"feedback": {"type": "string"}},
                        "required": ["feedback"],
                    },
                    "transition_to": "offer_call_option",
                }
            ],
        },
        "offer_call_option": {
            "task_messages": [
                {
                    "role": "system",
                    "content": (
                        "Offer a discovery call or email inquiry. "
                        "E.g., 'Would you prefer a video call with John George or to send an email?'"
                    ),
                }
            ],
            "functions": [
                {
                    "name": "offer_call_option",
                    "handler": offer_call_option,
                    "description": "Offer discovery call options",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "option": {"type": "string", "enum": ["book", "contact"]}
                        },
                        "required": ["option"],
                    },
                    "transition_to": "close_call",
                }
            ],
        },
        "close_call": {
            "task_messages": [
                {
                    "role": "system",
                    "content": (
                        "Thank the caller and end the conversation warmly. "
                        "E.g., 'Thank you for your interest. Have a great day!'"
                    ),
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
        # Replace these with your actual service configurations
        daily_room_url = (
            "https://your-daily-room-url"  # Replace with your Daily room URL
        )
        openai_api_key = "your-openai-api-key"  # Replace with your OpenAI API key
        deepgram_api_key = "your-deepgram-api-key"  # Replace with your Deepgram API key

        # Initialize transport
        transport = DailyTransport(
            room_url=daily_room_url,
            participant=None,
            assistant_name="Lead Qualification Bot",
            daily_params=DailyParams(
                audio_out_enabled=True,
                vad_enabled=True,
            ),
        )

        # Initialize services
        stt = DeepgramSTTService(api_key=deepgram_api_key)
        tts = DeepgramTTSService(api_key=deepgram_api_key, voice="aura-helios-en")
        llm = OpenAILLMService(api_key=openai_api_key, model="gpt-4o")

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
