"""Flow-based bot implementation using the base bot framework."""

import asyncio
from functools import partial
from typing import Dict
import sys
import uuid

from dotenv import load_dotenv
from loguru import logger

from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.frame_processor import FrameProcessor
from pipecat.processors.frameworks.rtvi import RTVIProcessor
from pipecat_flows import FlowArgs, FlowManager, FlowResult
from pipecat_flows.types import ContextStrategy, ContextStrategyConfig

from bots.base_bot import BaseBot
from config.settings import AppConfig
from prompts import (
    get_role_prompt,
    get_recording_consent_prompt,
    get_name_and_interest_prompt,
    get_consultancy_prompt,
    get_development_prompt,
    get_qa_prompt,
    get_any_more_questions_prompt,
    get_close_call_prompt,
)

# Load environment variables from .env file
load_dotenv()

# Configure logger
logger.remove(0)
logger.add(sys.stderr, level="DEBUG")


# ==============================================================================
# Node Configurations
# ==============================================================================


def create_recording_consent_node() -> Dict:
    """# Node 1: Recording Consent Node
    Create initial node that requests recording consent."""
    return {
        **get_role_prompt(),
        **get_recording_consent_prompt(),
        "functions": [
            {
                "type": "function",
                "function": {
                    "name": "collect_recording_consent",
                    "description": "Record whether the user consents to call recording",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "recording_consent": {
                                "type": "boolean",
                                "description": "Whether the user consents to call recording",
                            }
                        },
                        "required": ["recording_consent"],
                    },
                    "handler": collect_recording_consent,
                    "transition_callback": handle_recording_consent,
                },
            }
        ],
    }


def create_name_and_interest_node() -> Dict:
    """# Node 2: Collect Name and Interest Node
    Create node that collects user's name and primary interest."""
    return {
        **get_role_prompt(),
        **get_name_and_interest_prompt(),
        "functions": [
            {
                "type": "function",
                "function": {
                    "name": "collect_name_and_interest",
                    "description": "Collect user's name and primary interest",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "interest_type": {
                                "type": "string",
                                "enum": [
                                    "technical_consultation",
                                    "qa",
                                    "voice_agent_development",
                                ],
                            },
                        },
                        "required": ["interest_type"],
                    },
                    "handler": collect_name_and_interest,
                    "transition_callback": handle_name_and_interest,
                },
            }
        ],
    }


def create_consultancy_node() -> Dict:
    """# Node 3: Consultancy Node
    Create node for handling technical consultation path."""
    return {
        **get_role_prompt(),
        **get_consultancy_prompt(),
        "functions": [
            {
                "type": "function",
                "function": {
                    "name": "handle_any_more_questions",
                    "description": "Check if the user has more questions",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "any_more_questions": {
                                "type": "boolean",
                                "description": "Whether the user has more questions",
                            }
                        },
                        "required": ["any_more_questions"],
                    },
                    "handler": handle_any_more_questions,
                    "transition_callback": handle_any_more_questions_transition,
                },
            }
        ],
        "post_actions": [
            {
                "type": "execute_navigation",
                "path": "/consultancy",
                "message": "I've navigated you to our consultancy booking page where you can schedule a paid consultation with our founder.",
            }
        ],
    }


def create_development_node() -> Dict:
    """# Node 4: Development Node
    Create node for handling voice agent development path."""
    return {
        **get_role_prompt(),
        **get_development_prompt(),
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


def create_qa_node() -> Dict:
    """# Node 5: Q&A Node
    Create node for handling general questions about services."""
    return {
        **get_role_prompt(),
        **get_qa_prompt(),
        "functions": [
            {
                "type": "function",
                "function": {
                    "name": "handle_qa",
                    "description": "Handle Q&A interaction and determine next steps",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "any_more_questions": {
                                "type": "boolean",
                                "description": "Whether the user has more questions",
                            },
                            "switch_to_service": {
                                "type": "string",
                                "enum": [
                                    "technical_consultation",
                                    "voice_agent_development",
                                    "none",
                                ],
                                "description": "If user wants to switch to discussing a specific service",
                            },
                        },
                        "required": ["any_more_questions", "switch_to_service"],
                    },
                    "handler": handle_qa,
                    "transition_callback": handle_qa_transition,
                },
            }
        ],
    }


def create_any_more_questions_node() -> Dict:
    """# Node 6: Any More Questions Node
    Create node that asks if the user has any more questions."""
    return {
        **get_role_prompt(),
        **get_any_more_questions_prompt(),
        "functions": [
            {
                "type": "function",
                "function": {
                    "name": "handle_any_more_questions",
                    "description": "Process user response to determine if they have additional questions",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "any_more_questions": {
                                "type": "boolean",
                                "description": "Whether the user has more questions",
                            }
                        },
                        "required": ["any_more_questions"],
                    },
                    "handler": handle_any_more_questions,
                    "transition_callback": handle_any_more_questions_transition,
                },
            }
        ],
    }


def create_close_call_node() -> Dict:
    """# Node 7: Final Close Node
    Create node to conclude the conversation."""
    return {
        **get_role_prompt(),
        **get_close_call_prompt(),
        "functions": [],
        "post_actions": [{"type": "end_conversation"}],
    }


# ==============================================================================
# Function Handlers
# ==============================================================================


async def collect_recording_consent(args: FlowArgs) -> FlowResult:
    """Process recording consent collection."""
    return {"recording_consent": args["recording_consent"]}


async def collect_name_and_interest(args: FlowArgs) -> FlowResult:
    """Collect user's name (if provided) and primary interest."""
    return {"name": args.get("name"), "interest_type": args["interest_type"]}


async def collect_qualification_data(args: FlowArgs) -> FlowResult:
    """Process qualification data collection."""
    return {
        "use_case": args["use_case"],
        "timeline": args["timeline"],
        "budget": args["budget"],
        "feedback": args["feedback"],
    }


async def handle_qa(args: FlowArgs) -> FlowResult:
    """Process Q&A interaction."""
    return {
        "any_more_questions": args["any_more_questions"],
        "switch_to_service": args["switch_to_service"],
    }


async def handle_any_more_questions(args: FlowArgs) -> FlowResult:
    """Process user response about having additional questions."""
    return {"any_more_questions": args["any_more_questions"]}


# ==============================================================================
# Transition Callbacks
# ==============================================================================


async def handle_recording_consent(args: Dict, flow_manager: FlowManager):
    """Handle transition after collecting recording consent."""
    flow_manager.state.update(args)

    if args["recording_consent"]:
        await flow_manager.set_node("interest", create_name_and_interest_node())
    else:
        # If no consent, go directly to close call with contact form navigation
        close_node = create_close_call_node()
        close_node["pre_actions"] = [
            {
                "type": "tts_say",
                "text": "I understand. I've navigated you to our contact form where you can send us your questions or requirements in writing.",
            },
            {"type": "execute_navigation", "path": "/contact"},
        ]
        await flow_manager.set_node("close_call", close_node)


async def handle_name_and_interest(args: Dict, flow_manager: FlowManager):
    """Handle transition after collecting user's name and interest."""
    flow_manager.state.update(args)
    interest_type = args["interest_type"]
    if interest_type == "technical_consultation":
        await flow_manager.set_node("consultancy", create_consultancy_node())
    elif interest_type == "qa":
        await flow_manager.set_node("qa", create_qa_node())
    else:  # voice_agent_development
        await flow_manager.set_node("development", create_development_node())


async def handle_qualification_data(args: Dict, flow_manager: FlowManager):
    """Handle transition after collecting qualification data."""
    flow_manager.state.update(args)

    qualified = (
        bool(args.get("use_case"))
        and bool(args.get("timeline"))
        and args.get("budget", 0) >= 1000
        and bool(args.get("feedback"))
    )

    logger.debug(f"Qualified: {qualified} based on: {args}")

    # Create any more questions node with navigation as pre-action
    questions_node = create_any_more_questions_node()

    # Add TTS message and navigation as separate pre-actions
    nav_message = (
        "I've navigated you to our discovery call booking page where you can schedule a free consultation."
        if qualified
        else "I've navigated you to our contact form where you can send us more details about your requirements."
    )

    questions_node["pre_actions"] = [
        {"type": "tts_say", "text": nav_message},
        {
            "type": "execute_navigation",
            "path": "/discovery" if qualified else "/contact",
        },
    ]

    # Transition to any more questions node
    await flow_manager.set_node("any_more_questions", questions_node)


async def handle_qa_transition(args: Dict, flow_manager: FlowManager):
    """Handle transition after Q&A interaction."""
    flow_manager.state.update(args)

    if not args["any_more_questions"]:
        if args["switch_to_service"] == "technical_consultation":
            await flow_manager.set_node("consultancy", create_consultancy_node())
        elif args["switch_to_service"] == "voice_agent_development":
            await flow_manager.set_node("development", create_development_node())
        else:
            # No more questions and no service interest - go to close call
            close_node = create_close_call_node()
            close_node["pre_actions"] = [
                {
                    "type": "tts_say",
                    "text": "I've navigated you to our contact form where you can find more information and reach out to us with any future questions.",
                },
                {"type": "execute_navigation", "path": "/contact"},
            ]
            await flow_manager.set_node("close_call", close_node)


async def handle_any_more_questions_transition(args: Dict, flow_manager: FlowManager):
    """Handle transition after checking for additional questions."""
    flow_manager.state.update(args)

    if args["any_more_questions"]:
        await flow_manager.set_node("qa", create_qa_node())
    else:
        await flow_manager.set_node("close_call", create_close_call_node())


# ==============================================================================
# Navigation Handling
# ==============================================================================


class NavigationCoordinator:
    """Handles navigation between pages"""

    def __init__(
        self, rtvi: RTVIProcessor, llm: FrameProcessor, context: OpenAILLMContext
    ):
        self.rtvi = rtvi
        self.llm = llm
        self.context = context

    async def navigate(self, path: str) -> bool:
        """Handle navigation with error tracking"""
        try:
            logger.debug(f"Navigating to {path} from NavigationCoordinator")
            await self.rtvi.handle_function_call(
                function_name="navigate",
                tool_call_id=f"nav_{uuid.uuid4()}",
                arguments={"path": path},
                llm=self.llm,
                context=self.context,
                result_callback=None,
            )
            return True
        except Exception:
            return False


# ==============================================================================
# Bot Implementation
# ==============================================================================


class FlowBot(BaseBot):
    """Flow-based bot implementation with clean navigation separation."""

    def __init__(self, config: AppConfig):
        super().__init__(config, create_recording_consent_node()["role_messages"])

        # Initialize flow-specific components
        self.navigation_coordinator = None
        self.flow_manager = None

    async def _handle_first_participant(self):
        """Handle first participant by initializing flow manager."""
        # Set up navigation coordinator
        self.navigation_coordinator = NavigationCoordinator(
            rtvi=self.rtvi, llm=self.llm, context=self.context
        )

        # Set up flow manager
        self.flow_manager = FlowManager(
            task=self.task,
            llm=self.llm,
            context_aggregator=self.context_aggregator,
            context_strategy=ContextStrategyConfig(strategy=ContextStrategy.RESET),
        )

        # Register navigation action
        self.flow_manager.register_action(
            "execute_navigation",
            partial(
                self._handle_navigation_action, coordinator=self.navigation_coordinator
            ),
        )

        # Initialize flow
        await self.flow_manager.initialize()
        await self.flow_manager.set_node(
            "recording_consent", create_recording_consent_node()
        )

    async def _handle_navigation_action(
        self, action: dict, coordinator: NavigationCoordinator
    ):
        """Handle navigation with proper error handling."""
        logger.debug(f"Handling navigation action: {action}")
        path = action["path"]

        try:
            if not await coordinator.navigate(path):
                logger.error("Navigation action failed without exception")
                await self._handle_navigation_error()
        except Exception as e:
            logger.error(f"Navigation action failed with exception: {str(e)}")
            await self._handle_navigation_error()

    async def _handle_navigation_error(self):
        """Handle navigation errors by transitioning to error close node."""
        error_node = create_close_call_node()
        error_node["pre_actions"] = [
            {
                "type": "tts_say",
                "text": "I apologize, but I encountered an error while trying to navigate to the next page. Please try refreshing the page or contact support if the issue persists.",
            }
        ]
        await self.flow_manager.set_node("close_call", error_node)


async def main():
    """Setup and run the flow-based voice assistant."""
    import argparse
    from utils.run_helpers import run_bot

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Flow Bot Server")
    parser.add_argument(
        "-u", "--room-url", type=str, required=True, help="Daily room URL"
    )
    parser.add_argument(
        "-t", "--token", type=str, required=True, help="Authentication token"
    )

    # Optional arguments
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host address")
    parser.add_argument("--port", type=int, default=8000, help="Port number")
    parser.add_argument("--reload", action="store_true", help="Enable code reloading")
    parser.add_argument(
        "--bot-type",
        type=str,
        choices=["simple", "flow"],
        default="flow",
        help="Type of bot",
    )

    args = parser.parse_args()

    # Pass the room URL and token to the run_bot function
    await run_bot(FlowBot, AppConfig, room_url=args.room_url, token=args.token)


if __name__ == "__main__":
    asyncio.run(main())
