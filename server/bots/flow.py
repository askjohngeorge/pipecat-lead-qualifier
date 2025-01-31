"""Flow-based bot implementation using the base bot framework."""

import asyncio
from functools import partial
import sys
import uuid
from typing import Dict, Optional
from dotenv import load_dotenv
from loguru import logger

from utils.config import AppConfig
from utils.bot_framework import BaseBot
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.frame_processor import FrameProcessor
from pipecat.processors.frameworks.rtvi import RTVIProcessor
from pipecat_flows import FlowManager, FlowArgs, FlowResult


# Load environment variables from .env file
load_dotenv()

# Configure logger
logger.remove(0)
logger.add(sys.stderr, level="DEBUG")


# ==============================================================================
# Core Node Definitions
# ==============================================================================


def create_greeting_node() -> Dict:
    """Create initial greeting node that collects name and identifies service."""
    return {
        "role_messages": [
            {
                "role": "system",
                "content": """# Identity
You are Chris, a helpful voice assistant for John George Voice AI Solutions. You are accessible via a widget on the website. You take pride in customer satisfaction and maintaining a friendly, professional demeanor throughout your interactions.

# Style
- You are currently operating as a voice conversation, so use natural language and be concise.
- Maintain a warm, professional, and polite tone.
- After asking a question, wait for the caller to respond before moving to the next question. Never ask more than one question at a time.
- Do not go off-topic, ask, or answer any questions that are not related to the tasks.
- At each step, you will be given a set of instructions to follow with examples. Please follow these instructions carefully, hew closely to the examples provided, and avoid going off-topic.
- If you're unable to proceed to the next step, politely explain the call cannot progress until the caller provides the required information. Stay on topic and do not be distracted by other questions or comments.""",
            }
        ],
        "task_messages": [
            {
                "role": "system",
                "content": """## Instructions
1. Greet the caller warmly and introduce yourself as Chris from John George Voice AI solutions
2. Ask for their name
3. After getting their name, ask if they're interested in a technical consultation or voice agent development
4. If they ask who they'll be meeting with, tell them it will be John George, the founder
5. If they're unsure about the services:
   - Technical consultation: A paid meeting to discuss specific needs and get detailed advice
   - Voice agent development: Building a custom solution, starting with a free discovery call

## Examples
[You]: Hi there, I'm Chris from John George Voice AI solutions. May I know your name please?
[Caller]: John
[You]: Thank you John. Are you interested in a technical consultation or voice agent development?""",
            }
        ],
        "functions": [
            {
                "type": "function",
                "function": {
                    "name": "collect_initial_info",
                    "handler": collect_initial_info,
                    "description": "Collect name and service preference",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "service_type": {
                                "type": "string",
                                "enum": [
                                    "technical_consultation",
                                    "voice_agent_development",
                                ],
                            },
                        },
                        "required": ["service_type"],
                    },
                    "transition_callback": handle_initial_info,
                },
            }
        ],
    }


def create_consultancy_node() -> Dict:
    """Create node for handling technical consultation path."""
    return {
        "task_messages": [
            {
                "role": "system",
                "content": """## Instructions
Explain that you're navigating them to the consultancy booking page where they can schedule a paid consultation.
Mention that this requires an up-front payment which is non-refundable for no-shows or cancellations.
Advise them to provide detailed information when booking to help prepare for the call.""",
            }
        ],
        "functions": [],
        "post_actions": [
            {
                "type": "execute_navigation",
                "path": "/consultancy",
                "message": "I've navigated you to our consultancy booking page where you can schedule a paid consultation with our founder.",
            }
        ],
    }


def create_development_node() -> Dict:
    """Create node for handling voice agent development path."""
    return {
        "task_messages": [
            {
                "role": "system",
                "content": """## Instructions
Guide the caller through the qualification process:

1. Ask about their specific use case for voice AI
2. Inquire about their project timeline
3. Discuss budget (minimum £1,000)
4. Get feedback on the call quality
5. Qualify based on:
   - Specific use case provided
   - Timeline specified
   - Budget > £1,000
   - Positive interaction feedback

Navigate to:
- /discovery if qualified (free discovery call)
- /contact if not qualified (contact form)""",
            }
        ],
        "functions": [
            {
                "type": "function",
                "function": {
                    "name": "collect_qualification_data",
                    "handler": collect_qualification_data,
                    "description": "Collect qualification information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "use_case": {"type": "string"},
                            "timeline": {"type": "string"},
                            "budget": {"type": "integer"},
                            "feedback": {"type": "string"},
                        },
                        "required": ["use_case", "timeline", "budget", "feedback"],
                    },
                    "transition_callback": handle_qualification_data,
                },
            }
        ],
    }


def create_close_call_node() -> Dict:
    """Create node to conclude the conversation."""
    return {
        "task_messages": [
            {
                "role": "system",
                "content": """## Instructions
Thank the caller sincerely for their time and engagement. 
Conclude the conversation on a positive and friendly note.
Do not ask if they have any other questions.""",
            }
        ],
        "functions": [],
        "post_actions": [{"type": "end_conversation"}],
    }


# ==============================================================================
# Function Handlers
# ==============================================================================


async def collect_initial_info(args: FlowArgs) -> FlowResult:
    """Process initial information collection."""
    return {"name": args.get("name"), "service_type": args["service_type"]}


async def collect_qualification_data(args: FlowArgs) -> FlowResult:
    """Process qualification data collection."""
    return {
        "use_case": args["use_case"],
        "timeline": args["timeline"],
        "budget": args["budget"],
        "feedback": args["feedback"],
    }


# ==============================================================================
# Transition Handlers
# ==============================================================================


async def handle_initial_info(args: Dict, flow_manager: FlowManager):
    """Handle transition after collecting initial information."""
    flow_manager.state.update(args)

    if args["service_type"] == "technical_consultation":
        await flow_manager.set_node("consultancy", create_consultancy_node())
    else:
        await flow_manager.set_node("development", create_development_node())


async def handle_qualification_data(args: Dict, flow_manager: FlowManager):
    """Handle transition after collecting qualification data."""
    flow_manager.state.update(args)

    qualified = (
        bool(args.get("use_case"))
        and bool(args.get("timeline"))
        and args.get("budget", 0) > 1000
        and bool(args.get("feedback"))
    )

    nav_node = create_navigation_node()
    if qualified:
        nav_node["post_actions"][0].update(
            {
                "path": "/discovery",
                "message": "I've navigated you to our discovery call booking page where you can schedule a free consultation.",
            }
        )
    else:
        nav_node["post_actions"][0].update(
            {
                "path": "/contact",
                "message": "I've navigated you to our contact form where you can send us more details about your requirements.",
            }
        )

    await flow_manager.set_node("navigation", nav_node)
    await flow_manager.set_node("close_call", create_close_call_node())


# ==============================================================================
# Navigation Handling
# ==============================================================================


def create_navigation_node() -> Dict:
    """Create navigation node."""
    return {
        "task_messages": [{"role": "system", "content": "{{NAVIGATION_MESSAGE}}"}],
        "functions": [],
        "post_actions": [{"type": "execute_navigation"}],
    }


def create_navigation_error_node() -> Dict:
    """Create error handling node."""
    return {
        "task_messages": [
            {
                "role": "system",
                "content": "Inform the caller that an error occurred and ask them to try again later.",
            }
        ],
        "functions": [],
        "post_actions": [{"type": "end_conversation"}],
    }


class NavigationCoordinator:
    """Handles navigation between pages with proper error handling."""

    def __init__(
        self, rtvi: RTVIProcessor, llm: FrameProcessor, context: OpenAILLMContext
    ):
        self.rtvi = rtvi
        self.llm = llm
        self.context = context

    async def navigate(self, path: str) -> bool:
        """Handle navigation with error tracking."""
        try:
            await self.rtvi.handle_function_call(
                function_name="navigate",
                tool_call_id=f"nav_{uuid.uuid4()}",
                arguments={"path": path},
                llm=self.llm,
                context=self.context,
                result_callback=None,
            )
            return True
        except Exception as e:
            logger.error(f"Navigation failed to {path}: {str(e)}")
            return False


# ==============================================================================
# Bot Implementation
# ==============================================================================


class FlowBot(BaseBot):
    """Flow-based bot implementation with clean navigation separation."""

    def __init__(self, config: AppConfig):
        super().__init__(config)
        self.navigation_coordinator: Optional[NavigationCoordinator] = None
        self.flow_manager: Optional[FlowManager] = None

    async def _setup_services_impl(self):
        """Implementation-specific service setup."""
        initial_messages = create_greeting_node()["role_messages"]
        self.context = OpenAILLMContext(messages=initial_messages)
        self.context_aggregator = self.services.llm.create_context_aggregator(
            self.context
        )

    async def _create_transport(self, factory, url: str, token: str):
        """Implementation-specific transport creation."""
        return factory.create_flow_assistant_transport(url, token)

    async def _handle_first_participant(self):
        """Implementation-specific first participant handling."""
        await self.flow_manager.initialize()
        await self.flow_manager.set_node("greeting", create_greeting_node())

    def _create_pipeline_impl(self):
        """Implementation-specific pipeline setup."""
        self.navigation_coordinator = NavigationCoordinator(
            rtvi=self.rtvi, llm=self.services.llm, context=self.context
        )

        self.flow_manager = FlowManager(
            task=self.task,
            llm=self.services.llm,
            context_aggregator=self.pipeline_builder.context_aggregator,
            tts=self.services.tts,
        )

        self.flow_manager.register_action(
            "execute_navigation",
            partial(
                self._handle_navigation_action, coordinator=self.navigation_coordinator
            ),
        )

    async def _handle_navigation_action(
        self, action: dict, coordinator: NavigationCoordinator
    ):
        """Handle navigation with proper error handling."""
        path = action["path"]
        message = action.get("message")

        try:
            if await coordinator.navigate(path):
                await self.flow_manager.set_node("close_call", create_close_call_node())
                return
            else:
                logger.error("Navigation action failed without exception")
        except Exception as e:
            logger.error(f"Navigation action failed with exception: {str(e)}")

        await self.flow_manager.set_node(
            "navigation_error", create_navigation_error_node()
        )


async def main():
    """Setup and run the lead qualification agent."""
    from utils.run_helpers import run_bot

    await run_bot(FlowBot, AppConfig)


if __name__ == "__main__":
    asyncio.run(main())
