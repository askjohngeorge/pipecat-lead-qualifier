"""Flow-based bot implementation using the base bot framework."""

import asyncio
from datetime import datetime
from functools import partial
from typing import Dict
import sys

import pytz
from dotenv import load_dotenv
from loguru import logger

from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.frame_processor import FrameProcessor
from pipecat_flows import FlowArgs, FlowManager, FlowResult
from pipecat_flows.types import ContextStrategy, ContextStrategyConfig

from bots.base_bot import BaseBot
from utils.config import AppConfig
from prompts import ROLE_MAIN, ROLE_CONTEXT, ROLE_TASK, ROLE_SPECIFICS

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
        "role_messages": [
            {
                "role": "system",
                "content": f"""{ROLE_MAIN}

{ROLE_CONTEXT}

{ROLE_TASK}

{ROLE_SPECIFICS}""",
            }
        ],
        "task_messages": [
            {
                "role": "system",
                "content": """# Steps
1. Request Recording Consent
"Hi there, I'm Chris an AI voice assistant from John George Voice AI Solutions. For quality assurance purposes, this call will be recorded. Do you consent to this recording?"
~Never answer any questions or do anything else other than obtain recording consent~
- [ 1.1 If R = Yes ] → ~Set recording_consent=True, and thank the user~
- [ 1.2 If R = No ] → ~Set recording_consent=False~
- [ 1.3 If R = Asks why we need recording ] → "We record calls to improve our service quality and ensure we accurately capture your requirements."
- [ 1.4 If R = Any other response ] → "I'm afraid I need a clear yes or no - do you consent to this call being recorded?"
""",
            }
        ],
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
        "task_messages": [
            {
                "role": "system",
                "content": """# Steps
1. Name Collection
"May I know your name please?"
 - [ 1.1 If R = Gives name ] -> "Thank you <name>" ~Proceed to step 2~
 - [ 1.2 If R = Refuses to give name ] -> ~Proceed without a name to step 2~
 - [ 1.3 If R = Asks why we need their name ] -> "So I know how to address you."

2. Primary Interest Identification
"Could you tell me if you're interested in technical consultancy, or voice agent development?"
 - [ 2.1 If R = Technical consultancy ] → ~Silently record interest_type=technical_consultation, name as <name>~
 - [ 2.2 If R = Voice agent development ] → ~Silently record interest_type=voice_agent_development, name as <name>~
 - [ 2.3 If R = Unclear response ] → "To help me understand better: Are you interested in technical consultancy, or voice agent development?"
 - [ 2.4 If R = Asks for explanation ] → "Technical consultancy is a paid meeting where we discuss your specific needs and provide detailed advice. Voice agent development involves building a custom solution, starting with a free discovery call."
 - [ 2.5 If R = Asks other questions ] → ~Silently record interest_type=qa, name as <name>~
""",
            }
        ],
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
        "task_messages": [
            {
                "role": "system",
                "content": """# Steps
1. Consultancy Booking
~Use the `navigate` tool to navigate to `/consultancy`~
"I've navigated you to our consultancy booking page where you can set up a video conference with our founder to discuss your needs in more detail. Please note that this will require an up-front payment which is non-refundable in the case of no-show or cancellation. Please provide as much detail as you can when you book, to assist us in preparing for the call."
~Ask if they have any more questions~
 - [ 1.1 If R = No more questions ] -> ~This step is complete~
 - [ 1.2 If R = Has more questions ] -> ~Only answer questions directly related to the provision of our voice AI services, anything else can be asked during the consultation~
""",
            }
        ],
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
        "task_messages": [
            {
                "role": "system",
                "content": """# Steps
1. Use Case Elaboration
"What tasks or interactions are you hoping your voice AI agent will handle?"
 - [ 1.1 If R = Specific use case provided ] -> ~Record use case as `<use_case>`, go to step 2~
 - [ 1.2 If R = Vague response ] -> "To help me understand better, could you describe what you're hoping to achieve with this solution?"
 - [ 1.3 If R = Asks for examples ] -> ~Present these as examples: customer service inquiries, support, returns; lead qualification; appointment scheduling; cold or warm outreach~

2. Timeline Establishment
"What's your desired timeline for this project, and are there any specific deadlines?"
 - [ 2.1 If R = Specific or rough timeline provided ] -> ~Record timeline as `<timeline>`, go to step 3~
 - [ 2.2 If R = No timeline or ASAP ] -> "Just a rough estimate would be helpful - are we discussing weeks, months, or quarters for implementation?"

3. Budget Discussion
"What budget have you allocated for this project?"
 * Development services begin at £1,000 for a simple voice agent with a single external integration
 * Advanced solutions with multiple integrations and post-deployment testing can range up to £10,000
 * Custom platform development is available but must be discussed on a case-by-case basis
 * All implementations will require ongoing costs associated with call costs, to be discussed on a case-by-case basis
 * We also offer support packages for ongoing maintenance and updates, again to be discussed on a case-by-case basis
 - [ 3.1 If R = Budget > £1,000 ] -> ~Record budget as `<budget>`, go to step 4~
 - [ 3.2 If R = Budget < £1,000 or no budget provided ] -> ~Explain our development services begin at £1,000 and ask if this is acceptable~
 - [ 3.3 If R = Vague response ] -> ~attempt to clarify the budget~

4. Interaction Assessment
"Before we proceed, I'd like to quickly ask for your feedback on the call quality so far. You're interacting with the kind of system you might be considering purchasing, so it's important for us to ensure it meets your expectations. Could you please give us your thoughts on the speed, clarity, and naturalness of the interaction?"
~This step is complete~""",
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


def create_qa_node() -> Dict:
    """# Node 5: Q&A Node
    Create node for handling general questions about services."""
    return {
        "task_messages": [
            {
                "role": "system",
                "content": """# Steps
1. Handle General Questions
"Please feel free to ask any questions you have about our voice AI services."
* Common topics include:
* - Service offerings and capabilities
* - Technology and integration options
* - Pricing and timelines
* - Case studies and success stories
- [ 1.1 If R = Asks specific question ] → ~Provide clear, concise answer based on available information~
- [ 1.2 If R = No more questions ] → ~Proceed to Node #6 (close call)~
- [ 1.3 If R = Shows interest in services ] → "Would you like to discuss technical consultancy or voice agent development in more detail?"
- [ 1.4 If R = Question outside scope ] → "That's a bit outside my scope. I can best help with questions about our voice AI services, technical consultancy, or voice agent development. What would you like to know about those?"
""",
            }
        ],
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
        "task_messages": [
            {
                "role": "system",
                "content": """# Steps
1. Ask About Additional Questions
"Do you have any more questions about our services?"
- [ 1.1 If R = Yes, any affirmative response or a question ] → ~Set any_more_questions=True~
- [ 1.2 If R = Any other response ] → ~Set any_more_questions=False~
""",
            }
        ],
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
        "task_messages": [
            {
                "role": "system",
                "content": """# Steps
1. Close the Call
"Thank you for your time. We appreciate you choosing John George Voice AI Solutions. Goodbye."
- ~End the call~
""",
            }
        ],
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
    """Handles navigation between pages with proper error handling."""

    def __init__(self, llm: FrameProcessor, context: OpenAILLMContext):
        self.llm = llm
        self.context = context

    async def navigate(self, path: str) -> bool:
        """Handle navigation with error tracking."""
        try:
            # TODO: Implement navigation without RTVI
            # For now, just log and return success
            logger.info(f"Navigating to {path}")
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
        super().__init__(config, create_recording_consent_node()["role_messages"])

        # Initialize flow-specific components
        self.navigation_coordinator = None
        self.flow_manager = None

    async def _handle_first_participant(self):
        """Handle first participant by initializing flow manager."""
        # Set up navigation coordinator
        self.navigation_coordinator = NavigationCoordinator(
            llm=self.llm, context=self.context
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
