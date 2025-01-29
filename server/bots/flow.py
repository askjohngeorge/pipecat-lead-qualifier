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


# Node generator functions
def create_collect_name_node() -> Dict:
    """Create a node to greet the caller and collect their name."""
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
- If you perfectly follow your instructions, you will be rewarded with a bonus.""",
            }
        ],
        "task_messages": [
            {
                "role": "system",
                "content": """## Instructions
Greet the caller warmly with a friendly tone, introduce yourself as Chris, a voice AI agent representing John George Voice AI solutions, and ask the caller for their name.

## Example
[You]: Hi there, I'm Chris, a voice AI agent from John George Voice AI solutions. May I know your name, please?""",
            }
        ],
        "functions": [
            {
                "type": "function",
                "function": {
                    "name": "collect_name",
                    "handler": collect_name,
                    "description": "Record the caller's name.",
                    "parameters": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                        "required": ["name"],
                    },
                },
            },
        ],
    }


def create_identify_service_node() -> Dict:
    """Create a node to determine the service of interest."""
    return {
        "task_messages": [
            {
                "role": "system",
                "content": """## Instructions
Politely inquire about the service the caller is interested in. Present two options: technical consultation or voice agent development. 

A technical consultation is a paid meeting where we discuss your specific needs and advise on the best approach. Voice agent development is where we build a custom voice AI solution for you, and initially involves scheduling a free discovery call to discuss your needs.

Encourage them to provide a clear response if they respond ambiguously.

If they ask who the meeting will be with, tell them it will be John George, the founder of John George Voice AI Solutions.

## Examples
### Example 1
[You]: Are you interested in a technical consultation or voice agent development?
[Caller]: I'm interested in voice agent development.

### Example 2
[You]: Are you interested in a technical consultation or voice agent development?
[Caller]: I'm not sure.
[You]: No problem. A technical consultation is a paid meeting where we discuss your specific needs and advise on the best approach. Voice agent development is where we build a custom voice AI solution for you, and initially involves scheduling a free discovery call to discuss your needs. Which of these are you interested in?
[Caller]: I think I'm interested in a technical consultation.

### Example 3
[You]: Are you interested in a technical consultation or voice agent development?
[Caller]: I'm interested in both.
[You]: I see. A technical consultation is a paid meeting where we discuss your specific needs and advise on the best approach. Voice agent development is where we build a custom voice AI solution for you, and initially involves scheduling a free discovery call to discuss your needs. Which of these are you interested in pursuing first?
[Caller]: Let's start with voice agent development.

### Example 4
[You]: Are you interested in a technical consultation or voice agent development?
[Caller]: Who would I be meeting with?
[You]: You would be meeting with John George, the founder of John George Voice AI Solutions. Now, are you interested in a technical consultation or voice agent development?
[Caller]: I'm interested in a technical consultation.
""",
            }
        ],
        "functions": [
            {
                "type": "function",
                "function": {
                    "name": "identify_service",
                    "handler": identify_service,
                    "description": "Record the caller's service preference.",
                    "parameters": {
                        "type": "object",
                        "properties": {
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
                },
            },
        ],
    }


def create_identify_use_case_node() -> Dict:
    """Create a node to gather details about the caller's use case."""
    return {
        "task_messages": [
            {
                "role": "system",
                "content": """## Instructions
Ask the caller to elaborate on their specific use case or requirements for voice agent development. Encourage them to provide as much detail as possible about their goals and desired outcomes.

If they respond ambiguously at first, prompt them to be more specific.

## Examples
### Example 1
[You]: Could you tell me more about your specific use case for voice agent development?
[Caller]: I want to automate customer service.

### Example 2
[You]: Could you tell me more about your specific use case for voice agent development?
[Caller]: I'm not sure.
[You]: No problem. To help me understand better, could you describe what you're hoping to achieve with a voice AI solution? What kind of tasks or interactions would you like it to handle?
[Caller]: I want to automate appointment bookings.

### Example 3
[You]: Could you tell me more about your specific use case for voice agent development?
[Caller]: I want to improve my business.
[You]: I see. To help me understand better, could you describe what you're hoping to achieve with a voice AI solution? What kind of tasks or interactions would you like it to handle?
[Caller]: I want to automate lead qualification.
""",
            }
        ],
        "functions": [
            {
                "type": "function",
                "function": {
                    "name": "identify_use_case",
                    "handler": identify_use_case,
                    "description": "Record the caller's specific use case for voice agent development.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "use_case": {"type": "string"},
                        },
                        "required": ["use_case"],
                    },
                },
            },
        ],
    }


def create_establish_timescales_node() -> Dict:
    """Create a node to determine the caller's timeline."""
    return {
        "task_messages": [
            {
                "role": "system",
                "content": "Ask the caller to share their desired timeline for the project. If applicable (based on their initial response), request details about specific deadlines or time constraints they may have.",
            }
        ],
        "functions": [
            {
                "type": "function",
                "function": {
                    "name": "establish_timescales",
                    "handler": establish_timescales,
                    "description": "Record the caller's timeline or deadline preferences for the project.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "timeline": {"type": "string"},
                        },
                        "required": ["timeline"],
                    },
                },
            },
        ],
    }


def create_determine_budget_node() -> Dict:
    """Create a node to discuss budget."""
    return {
        "task_messages": [
            {
                "role": "system",
                "content": """## Primary Response
"What budget range did you have in mind for this project?"

## Cost Details (Only share if explicitly asked)
### Basic Solution
- Starting from £1,000
- Includes:
  - Single integration
  - Basic testing
  - Initial voice agent setup

### Advanced Implementation
- Typically up to £10,000
- Includes:
  - Multiple integrations
  - Comprehensive testing
  - Complex configurations

### Custom Platform Development
- Will have to be discussed on a case-by-case basis

### Additional Costs Notice
**Please note**: All implementations include:
- Ongoing usage fees
- Ongoing support costs""",
            }
        ],
        "functions": [
            {
                "type": "function",
                "function": {
                    "name": "determine_budget",
                    "handler": determine_budget,
                    "description": "Record the caller's budget information for the project.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "budget": {"type": "integer"},
                        },
                        "required": ["budget"],
                    },
                },
            },
        ],
    }


def create_record_feedback_node() -> Dict:
    """Create a node to assess interaction quality."""
    return {
        "task_messages": [
            {
                "role": "system",
                "content": "Ask the caller to assess the quality of the interaction so far, in terms of latency, clarity, and naturalness.",
            }
        ],
        "functions": [
            {
                "type": "function",
                "function": {
                    "name": "record_feedback",
                    "handler": record_feedback,
                    "description": "Record the caller's feedback on the interaction.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "feedback": {"type": "string"},
                        },
                        "required": ["feedback"],
                    },
                },
            },
        ],
    }


def create_navigation_node() -> Dict:
    """Single reusable node for all navigation paths"""
    return {
        "task_messages": [
            {
                "role": "system",
                "content": "{{NAVIGATION_MESSAGE}}",  # Template placeholder
            }
        ],
        "functions": [
            {
                "type": "function",
                "function": {
                    "name": "navigate",
                    "handler": navigate,
                    "description": "Handle path navigation",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "enum": ["/consultancy", "/discovery", "/contact"],
                            }
                        },
                        "required": ["path"],
                    },
                },
            }
        ],
        "post_actions": [{"type": "execute_navigation"}],
    }


def create_error_node() -> Dict:
    """Create a node to handle errors"""
    return {
        "task_messages": [
            {
                "role": "system",
                "content": "Inform the caller that an error has occurred, and politely ask them to try again later.",
            }
        ],
        "functions": [],
        "post_actions": [{"type": "end_conversation"}],
    }


def create_close_node() -> Dict:
    """Create a node to conclude the conversation."""
    return {
        "task_messages": [
            {
                "role": "system",
                "content": "Ask the caller if they have any other questions or if they would like to discuss anything else. Once they are satisfied, thank them sincerely for their time and engagement. Conclude the conversation on a positive and friendly note, wishing them a great rest of their day.",
            }
        ],
        "functions": [],
        "post_actions": [{"type": "end_conversation"}],
    }


# Function handlers
async def collect_name(args: FlowArgs) -> FlowResult:
    """Process name collection."""
    return {"name": args["name"]}


async def identify_service(args: FlowArgs) -> FlowResult:
    """Process service type identification."""
    return {"service_type": args["service_type"]}


async def identify_use_case(args: FlowArgs) -> FlowResult:
    """Process use case identification."""
    return {"use_case": args["use_case"]}


async def establish_timescales(args: FlowArgs) -> FlowResult:
    """Process timeline establishment."""
    return {"timeline": args["timeline"]}


async def determine_budget(args: FlowArgs) -> FlowResult:
    """Process budget determination."""
    return {"budget": args["budget"]}


async def record_feedback(args: FlowArgs) -> FlowResult:
    """Process interaction assessment."""
    return {"feedback": args["feedback"]}


async def navigate(args: FlowArgs) -> FlowResult:
    """Handle transition after navigate."""
    path = args["path"]
    logger.debug(f"navigating to {path} in navigate")
    return {"path": path}


# Transition handlers
async def handle_collect_name(args: Dict, flow_manager: FlowManager):
    """Handle transition after name collection."""
    flow_manager.state["name"] = args["name"]
    await flow_manager.set_node("service_inquiry", create_identify_service_node())


async def handle_identify_service(args: Dict, flow_manager: FlowManager):
    """Handle transition after service identification."""
    flow_manager.state["service_type"] = args["service_type"]
    if args["service_type"] == "technical_consultation":
        # Get the generic navigation node
        nav_node = create_navigation_node()

        # Set navigation message and path
        message = "I'll navigate you to the consultancy booking page where you can schedule a meeting to discuss your requirements further."
        path = "/consultancy"

        # Inject dynamic message
        nav_node["task_messages"][0]["content"] = message

        # Set navigation parameters in post-actions
        nav_node["post_actions"][0]["path"] = path
        nav_node["post_actions"][0]["message"] = message

        await flow_manager.set_node("navigation", nav_node)
    else:  # voice_agent_development
        await flow_manager.set_node(
            "identify_use_case", create_identify_use_case_node()
        )


async def handle_identify_use_case(args: Dict, flow_manager: FlowManager):
    """Handle transition after use case identification."""
    flow_manager.state["use_case"] = args["use_case"]
    await flow_manager.set_node(
        "establish_timescales", create_establish_timescales_node()
    )


async def handle_establish_timescales(args: Dict, flow_manager: FlowManager):
    """Handle transition after timeline establishment."""
    flow_manager.state["timeline"] = args["timeline"]
    await flow_manager.set_node("determine_budget", create_determine_budget_node())


async def handle_determine_budget(args: Dict, flow_manager: FlowManager):
    """Handle transition after budget determination."""
    flow_manager.state["budget"] = args["budget"]
    await flow_manager.set_node("record_feedback", create_record_feedback_node())


async def handle_record_feedback(args: Dict, flow_manager: FlowManager):
    """Handle transition after interaction assessment."""
    service_type = flow_manager.state["service_type"]
    use_case = flow_manager.state["use_case"]
    timeline = flow_manager.state["timeline"]
    budget = flow_manager.state["budget"]
    feedback = args["feedback"]
    flow_manager.state["feedback"] = feedback

    qualified = (
        service_type == "voice_agent_development"
        and use_case
        and timeline
        and budget > 1000
        and feedback
    )

    # Get the generic navigation node
    nav_node = create_navigation_node()

    if qualified:
        message = "I'll navigate you to our discovery page where you can learn more about available solutions and schedule a consultation."
        path = "/discovery"
    else:
        message = "I'll navigate you to our contact form page which you can use to send an email to the team."
        path = "/contact"

    # Inject dynamic message
    nav_node["task_messages"][0]["content"] = message

    # Set navigation parameters in post-actions
    nav_node["post_actions"][0]["path"] = path
    nav_node["post_actions"][0]["message"] = message

    await flow_manager.set_node("navigation", nav_node)


async def handle_navigate(args: Dict, flow_manager: FlowManager):
    """Single handler for all navigation"""
    path = args["path"]
    logger.debug(f"Preparing navigation to {path}")
    # Actual navigation happens in the action, this just passes through


# Transition callback mapping
HANDLERS = {
    "collect_name": handle_collect_name,
    "identify_service": handle_identify_service,
    "identify_use_case": handle_identify_use_case,
    "establish_timescales": handle_establish_timescales,
    "determine_budget": handle_determine_budget,
    "record_feedback": handle_record_feedback,
    "navigate": handle_navigate,
}


async def handle_lead_qualification_transition(
    function_name: str, args: Dict, flow_manager: FlowManager
):
    """Handle transitions between lead qualification flow states."""
    logger.debug(f"Processing {function_name} transition with args: {args}")
    await HANDLERS[function_name](args, flow_manager)


class NavigationCoordinator:
    """Handles navigation between pages with proper error handling"""

    def __init__(
        self, rtvi: RTVIProcessor, llm: FrameProcessor, context: OpenAILLMContext
    ):
        self.rtvi = rtvi
        self.llm = llm
        self.context = context

    async def navigate(self, path: str) -> bool:
        """Handle navigation with error tracking"""
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


class FlowBot(BaseBot):
    """Flow-based bot implementation with clean navigation separation"""

    def __init__(self, config: AppConfig):
        super().__init__(config)
        self.navigation_coordinator: Optional[NavigationCoordinator] = None
        self.flow_manager: Optional[FlowManager] = None

    async def _setup_services_impl(self):
        """Implementation-specific service setup."""
        initial_messages = create_collect_name_node()["role_messages"]
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
        await self.flow_manager.set_node("collect_name", create_collect_name_node())

    def _create_pipeline_impl(self):
        """Implementation-specific pipeline setup"""
        # Initialize core components first
        self.navigation_coordinator = NavigationCoordinator(
            rtvi=self.rtvi, llm=self.services.llm, context=self.context
        )

        # Configure FlowManager
        self.flow_manager = FlowManager(
            task=self.task,
            llm=self.services.llm,
            context_aggregator=self.pipeline_builder.context_aggregator,
            tts=self.services.tts,
            transition_callback=handle_lead_qualification_transition,
        )

        # Register navigation action with coordinator reference
        self.flow_manager.register_action(
            "execute_navigation",
            partial(
                self._handle_navigation_action, coordinator=self.navigation_coordinator
            ),
        )

    async def _handle_navigation_action(
        self, action: dict, coordinator: NavigationCoordinator
    ):
        """Encapsulated navigation handler with coordinator access"""
        path = action["path"]
        message = action.get("message")

        try:
            if message:
                await self.flow_manager.action_manager.execute_actions(
                    [{"type": "tts_say", "text": message}]
                )

            if await coordinator.navigate(path):
                await self.flow_manager.set_node("close_call", create_close_node())
            else:
                logger.error("Navigation failed, staying in current node")

        except Exception as e:
            logger.error(f"Navigation action failed: {str(e)}")
            await self.flow_manager.set_node("error_state", create_error_node())


async def main():
    """Setup and run the lead qualification agent."""
    from utils.run_helpers import run_bot

    await run_bot(FlowBot, AppConfig)


if __name__ == "__main__":
    asyncio.run(main())
