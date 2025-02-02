"""Flow-based bot implementation using the base bot framework."""

import asyncio
from datetime import datetime
from functools import partial
import sys
import uuid
from typing import Dict, Optional

import pytz
from dotenv import load_dotenv
from loguru import logger

from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.frame_processor import FrameProcessor
from pipecat.processors.frameworks.rtvi import RTVIProcessor
from pipecat_flows import FlowArgs, FlowManager, FlowResult

from utils.bot_framework import BaseBot
from utils.config import AppConfig


# Load environment variables from .env file
load_dotenv()

# Configure logger
logger.remove(0)
logger.add(sys.stderr, level="DEBUG")


# ==============================================================================
# Core Node Definitions
# ==============================================================================


def create_greeting_node() -> Dict:
    """# REDUNDANT: create_greeting_node is not used in the current flow tree.
    Create initial greeting node that collects name and identifies service."""
    return {
        "role_messages": [
            {
                "role": "system",
                "content": f"""# Role
You are Chris, a helpful voice assistant for John George Voice AI Solutions.

# Context
You are accessible via a widget on the website. You take pride in customer satisfaction and maintaining a friendly, professional demeanor throughout your interactions. You are currently operating as a voice conversation.

# Task
Your primary task is to qualify leads by guiding them through a series of questions to determine their needs and fit for John George Voice AI Solutions' offerings. You must follow the conversation flow provided below to collect necessary information and navigate the conversation accordingly.

# Specifics
- [ #.# CONDITION ] this is a condition block, which acts as identifiers of the user's intent and guides conversation flow. The agent should remain in the current step, attempting to match user responses to conditions within that step, until explicitly instructed to proceed to a different step. "R =" means "the user's response was".
- <variable> is a variable block, which should ALWAYS be substituted by the information the user has provided. For example, if the user's name is given as `<name>`, you might say "Thank you <name>".
- The symbol ~ indicates an instruction you should follow but not say aloud, eg ~Go to step 8~.
- Sentences in double quotes `"Example sentence."` should be said verbatim, unless it would be incoherent or sound unnatural for the context of the conversation.
- Lines that begin with a * are to provide context and clarity. You don't need to say these, but if asked, you can use the information for reference in answering questions.
- You may only ask one question at a time. Wait for a response after each question you ask.
- Follow the script closely but dynamically.
- Today's day of the week and date in the UK is: {datetime.now(pytz.timezone('Europe/London')).strftime('%A, %d %B %Y')}""",
            }
        ],
        "task_messages": [
            {
                "role": "system",
                "content": """# Steps
1. Name Collection
"Hi there, I'm Chris from John George Voice AI solutions. May I know your name please?"
 - [ 1.1 If R = Gives name ] -> "Thank you <name>" ~Record name as `<name>`, go to step 2~
 - [ 1.2 If R = Asks why we need their name ] -> "So I know how to address you."
 - [ 1.3 If R = Uncomfortable providing name ] -> "I understand. How would you like to be addressed?"
 - [ 1.4 If R = Refuses to give name ] -> ~Go to step 2 without using a name going forward~

2. Service Identification
"Are you interested in a technical consultation or voice agent development?"
 * A technical consultation is a paid meeting where we discuss their specific needs and provide detailed advice on the best approach.
 * Voice agent development involves building a custom solution, starting with a free discovery call to discuss their needs.
 - [ 2.1 If R = Technical consultation ] -> ~Record service type as `technical_consultation`~
 - [ 2.2 If R = Voice agent development ] -> ~Record service type as `voice_agent_development`~
 - [ 2.3 If R = Ambiguous response ] -> "To help me understand better: Are you interested in a technical consultation, or voice agent development as described?"
 - [ 2.4 If R = Interested in both ] -> "We recommend starting with voice agent development as that includes initial discovery discussions. Shall we proceed with that?"
 - [ 2.5 If R = Asked about meeting host ] -> "You'd be meeting with John George, our founder. Which service are you interested in?"
 - [ 2.6 If R = Unrecognised response ] -> "I'm sorry, I didn't understand. Could you please clarify if you are interested in a technical consultation or voice agent development?""",
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


def create_permission_node() -> Dict:
    """# Node 1: Permission Node
    Create initial node that requests recording consent."""
    return {
        "role_messages": [
            {
                "role": "system",
                "content": f"""# Role
You are Chris, a helpful voice assistant for John George Voice AI Solutions.

# Context
You are accessible via a widget on the website. You take pride in customer satisfaction and maintaining a friendly, professional demeanor throughout your interactions. You are currently operating as a voice conversation.

# Task
Your primary task is to qualify leads by guiding them through a series of questions to determine their needs and fit for John George Voice AI Solutions' offerings. You must follow the conversation flow provided below to collect necessary information and navigate the conversation accordingly.

# Specifics
- [ #.# CONDITION ] this is a condition block, which acts as identifiers of the user's intent and guides conversation flow. The agent should remain in the current step, attempting to match user responses to conditions within that step, until explicitly instructed to proceed to a different step. "R =" means "the user's response was".
- <variable> is a variable block, which should ALWAYS be substituted by the information the user has provided. For example, if the user's name is given as `<name>`, you might say "Thank you <name>".
- The symbol ~ indicates an instruction you should follow but not say aloud, eg ~Go to step 8~.
- Sentences in double quotes `"Example sentence."` should be said verbatim, unless it would be incoherent or sound unnatural for the context of the conversation.
- Lines that begin with a * are to provide context and clarity. You don't need to say these, but if asked, you can use the information for reference in answering questions.
- You may only ask one question at a time. Wait for a response after each question you ask.
- Follow the script closely but dynamically.
- Today's day of the week and date in the UK is: {datetime.now(pytz.timezone('Europe/London')).strftime('%A, %d %B %Y')}""",
            }
        ],
        "task_messages": [
            {
                "role": "system",
                "content": """# Steps
1. Request Recording Consent
"For quality assurance purposes, this call will be recorded. Do you consent to this recording?"
- [ 1.1 If R = Yes ] → ~Set recording_consent=True, then proceed to Node #2~
- [ 1.2 If R = No ] → ~Set recording_consent=False, then go directly to Node #6 (close call)~
- [ 1.3 If R = Asks why we need recording ] → "We record calls to improve our service quality and ensure we accurately capture your requirements."
- [ 1.4 If R = Unclear response ] → "I need a clear yes or no - do you consent to this call being recorded?"
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


def create_interest_node() -> Dict:
    """# Node 2: Interest Node
    Create node that identifies user's primary interest."""
    return {
        "task_messages": [
            {
                "role": "system",
                "content": """# Steps
1. Identify Primary Interest
"Could you tell me if you're calling about technical consultancy, general questions, or voice agent development?"
- [ 1.1 If R = Technical consultancy ] → ~Set interest_type=technical_consultation, then proceed to Node #3~
- [ 1.2 If R = General questions/Q&A ] → ~Set interest_type=qa, then proceed to Node #4~
- [ 1.3 If R = Voice agent development ] → ~Set interest_type=voice_agent_development, then proceed to Node #5~
- [ 1.4 If R = Unclear response ] → "To help me understand better: Are you interested in technical consultancy, general questions about our services, or voice agent development?"
- [ 1.5 If R = Asks for explanation ] → "Technical consultancy is a paid meeting where we discuss your specific needs and provide detailed advice. Voice agent development involves building a custom solution, starting with a free discovery call. Or I can answer general questions about our services. Which interests you?"
""",
            }
        ],
        "functions": [
            {
                "type": "function",
                "function": {
                    "name": "collect_interest",
                    "description": "Record the user's primary interest",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "interest_type": {
                                "type": "string",
                                "enum": [
                                    "technical_consultation",
                                    "qa",
                                    "voice_agent_development",
                                ],
                                "description": "The type of service the user is interested in",
                            }
                        },
                        "required": ["interest_type"],
                    },
                    "handler": collect_interest,
                    "transition_callback": handle_interest,
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
                            "has_more_questions": {
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
                        "required": ["has_more_questions", "switch_to_service"],
                    },
                    "handler": handle_qa,
                    "transition_callback": handle_qa_transition,
                },
            }
        ],
    }


def create_close_call_node() -> Dict:
    """# Node 6: Close Call Node
    Create node to conclude the conversation."""
    return {
        "task_messages": [
            {
                "role": "system",
                "content": """# Steps
1. Any more questions?
~Ask if they have any more questions~
 - [ 1.1 If R = No more questions ] -> ~Go to step 2~
 - [ 1.2 If R = Has more questions ] -> ~Only answer questions directly related to the provision of our voice AI services, anything else can be asked during the consultation~
 
 2. Close the Call
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


async def collect_initial_info(args: FlowArgs) -> FlowResult:
    """Process initial information collection."""
    return {"name": args.get("name"), "service_type": args["service_type"]}


async def collect_recording_consent(args: FlowArgs) -> FlowResult:
    """Process recording consent collection."""
    return {"recording_consent": args["recording_consent"]}


async def collect_interest(args: FlowArgs) -> FlowResult:
    """Process interest type collection."""
    return {"interest_type": args["interest_type"]}


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
        "has_more_questions": args["has_more_questions"],
        "switch_to_service": args["switch_to_service"],
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


async def handle_recording_consent(args: Dict, flow_manager: FlowManager):
    """Handle transition after collecting recording consent."""
    flow_manager.state.update(args)

    if args["recording_consent"]:
        await flow_manager.set_node("interest", create_interest_node())
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


async def handle_interest(args: Dict, flow_manager: FlowManager):
    """Handle transition after collecting interest type."""
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

    # Create close call node with navigation as pre-action
    close_node = create_close_call_node()

    # Add TTS message and navigation as separate pre-actions
    nav_message = (
        "I've navigated you to our discovery call booking page where you can schedule a free consultation."
        if qualified
        else "I've navigated you to our contact form where you can send us more details about your requirements."
    )

    close_node["pre_actions"] = [
        {"type": "tts_say", "text": nav_message},
        {
            "type": "execute_navigation",
            "path": "/discovery" if qualified else "/contact",
        },
    ]

    # Transition directly to close call node
    await flow_manager.set_node("close_call", close_node)


async def handle_qa_transition(args: Dict, flow_manager: FlowManager):
    """Handle transition after Q&A interaction."""
    flow_manager.state.update(args)

    if not args["has_more_questions"]:
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


# ==============================================================================
# Navigation Handling
# ==============================================================================


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
        initial_messages = create_permission_node()["role_messages"]
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
        await self.flow_manager.set_node("permission", create_permission_node())

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
        path = action["path"]  # Message is now handled by tts_say action

        try:
            if not await coordinator.navigate(path):
                logger.error("Navigation action failed without exception")
                # On navigation failure, proceed to close call with error message
                error_node = create_close_call_node()
                error_node["pre_actions"] = [
                    {
                        "type": "tts_say",
                        "text": "I apologize, but I encountered an error while trying to navigate to the next page. Please try refreshing the page or contact support if the issue persists.",
                    }
                ]
                await self.flow_manager.set_node("close_call", error_node)
        except Exception as e:
            logger.error(f"Navigation action failed with exception: {str(e)}")
            # Handle exception similarly
            error_node = create_close_call_node()
            error_node["pre_actions"] = [
                {
                    "type": "tts_say",
                    "text": "I apologize, but I encountered an error while trying to navigate to the next page. Please try refreshing the page or contact support if the issue persists.",
                }
            ]
            await self.flow_manager.set_node("close_call", error_node)


async def main():
    """Setup and run the lead qualification agent."""
    from utils.run_helpers import run_bot

    await run_bot(FlowBot, AppConfig)


if __name__ == "__main__":
    asyncio.run(main())
