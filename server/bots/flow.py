"""Flow-based bot implementation using the base bot framework."""

import asyncio
import sys
import uuid
from typing import Dict, Literal, Optional
from dotenv import load_dotenv
from loguru import logger
from pydantic import BaseModel

from utils.config import AppConfig
from utils.bot_framework import BaseBot
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat_flows import FlowManager, FlowConfig, FlowArgs, FlowResult


class NavigationEventData(BaseModel):
    """Data structure for navigation events."""

    path: str
    query: Optional[dict] = None
    replace: bool = False


class NavigationEventMessage(BaseModel):
    """RTVI message for navigation events."""

    label: Literal["rtvi-ai"] = "rtvi-ai"
    type: Literal["navigation-request"] = "navigation-request"
    id: str
    data: NavigationEventData


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
                "content": "You are a lead qualification agent. Your responses will be converted to audio. Keep responses natural, friendly, and terse.",
            }
        ],
        "task_messages": [
            {
                "role": "system",
                "content": "Greet the caller warmly with a friendly tone, introduce yourself as Chris, a voice AI agent representing John George Voice AI solutions, and ask the caller for their name.",
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


def create_service_inquiry_node() -> Dict:
    """Create a node to determine the service of interest."""
    return {
        "task_messages": [
            {
                "role": "system",
                "content": "Politely inquire about the service the caller is interested in. Present two options: technical consultation or voice agent development. Encourage them to provide a clear response if they respond ambiguously.",
            }
        ],
        "functions": [
            {
                "type": "function",
                "function": {
                    "name": "identify_service",
                    "handler": identify_service,
                    "description": "Record the caller's service preference (one of 'technical consultation' or 'voice agent development').",
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


def create_use_case_node() -> Dict:
    """Create a node to gather details about the caller's use case."""
    return {
        "task_messages": [
            {
                "role": "system",
                "content": "Ask the caller to elaborate on their specific use case or requirements for voice agent development. Encourage them to provide as much detail as possible about their goals and desired outcomes if they respond ambiguously at first.",
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


def create_timescales_node() -> Dict:
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


def create_budget_node() -> Dict:
    """Create a node to discuss budget."""
    return {
        "task_messages": [
            {
                "role": "system",
                "content": "Ask about their budget for the project.",
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
                            "budget": {"type": "string"},
                        },
                        "required": ["budget"],
                    },
                },
            },
        ],
    }


def create_interaction_assessment_node() -> Dict:
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
                    "name": "assess_interaction",
                    "handler": assess_interaction,
                    "description": "Record the reported interaction quality and determine if the caller is qualified.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "qualified": {"type": "boolean"},
                        },
                        "required": ["qualified"],
                    },
                },
            },
        ],
    }


def create_redirect_consultancy_node() -> Dict:
    """Create a node to redirect the caller to the consultancy page."""
    return {
        "task_messages": [
            {
                "role": "system",
                "content": "Inform the caller that you will redirect them to the consultancy booking page where they can schedule a meeting to discuss their requirements further.",
            }
        ],
        "functions": [
            {
                "type": "function",
                "function": {
                    "name": "redirect_consultancy",
                    "handler": redirect_consultancy,
                    "description": "Redirect the caller to the consultancy booking page.",
                    "parameters": {
                        "type": "object",
                        "properties": {"redirect": {"type": "string"}},
                        "required": ["redirect"],
                    },
                },
            }
        ],
    }


def create_redirect_discovery_node() -> Dict:
    """Create a node to redirect the caller to the discovery page."""
    return {
        "task_messages": [
            {
                "role": "system",
                "content": "Inform the caller that you will redirect them to the discovery booking page where they can learn more about available solutions and schedule a consultation.",
            }
        ],
        "functions": [
            {
                "type": "function",
                "function": {
                    "name": "redirect_discovery",
                    "handler": redirect_discovery,
                    "description": "Redirect the caller to the discovery booking page.",
                    "parameters": {
                        "type": "object",
                        "properties": {"redirect": {"type": "string"}},
                        "required": ["redirect"],
                    },
                },
            }
        ],
    }


def create_close_node() -> Dict:
    """Create a node to conclude the conversation."""
    return {
        "task_messages": [
            {
                "role": "system",
                "content": "Thank the caller sincerely for their time and engagement. Conclude the conversation on a positive and friendly note, wishing them a great day.",
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


async def assess_interaction(args: FlowArgs) -> FlowResult:
    """Process interaction assessment."""
    return {"qualified": args["qualified"]}


async def redirect_consultancy(args: FlowArgs) -> FlowResult:
    """Handle transition after redirect."""
    return {"redirect": args["redirect"]}


async def redirect_discovery(args: FlowArgs) -> FlowResult:
    """Handle transition after redirect."""
    return {"redirect": args["redirect"]}


# Transition handlers
async def handle_name_collection(args: Dict, flow_manager: FlowManager):
    """Handle transition after name collection."""
    flow_manager.state["name"] = args["name"]
    await flow_manager.set_node("service_inquiry", create_service_inquiry_node())


async def handle_service_identification(args: Dict, flow_manager: FlowManager):
    """Handle transition after service identification."""
    flow_manager.state["service_type"] = args["service_type"]
    if args["service_type"] == "technical_consultation":
        await flow_manager.set_node(
            "redirect_consultancy", create_redirect_consultancy_node()
        )
    else:  # voice_agent_development
        await flow_manager.set_node("identify_use_case", create_use_case_node())


async def handle_use_case_identification(args: Dict, flow_manager: FlowManager):
    """Handle transition after use case identification."""
    flow_manager.state["use_case"] = args["use_case"]
    await flow_manager.set_node("establish_timescales", create_timescales_node())


async def handle_timescales_establishment(args: Dict, flow_manager: FlowManager):
    """Handle transition after timeline establishment."""
    flow_manager.state["timeline"] = args["timeline"]
    await flow_manager.set_node("determine_budget", create_budget_node())


async def handle_budget_determination(args: Dict, flow_manager: FlowManager):
    """Handle transition after budget determination."""
    flow_manager.state["budget"] = args["budget"]
    await flow_manager.set_node(
        "assess_interaction", create_interaction_assessment_node()
    )


async def handle_interaction_assessment(args: Dict, flow_manager: FlowManager):
    """Handle transition after interaction assessment."""
    flow_manager.state["qualified"] = args["qualified"]
    if args["qualified"]:
        await flow_manager.set_node(
            "redirect_discovery", create_redirect_discovery_node()
        )
    else:
        await flow_manager.set_node(
            "redirect_consultancy", create_redirect_consultancy_node()
        )


async def handle_redirect_consultancy(args: Dict, flow_manager: FlowManager):
    """Handle transition after redirect."""
    logger.debug("Redirecting to consultancy page in handle_redirect_consultancy")
    await flow_manager.request_navigation("/consultancy")
    await flow_manager.set_node("close_call", create_close_node())


async def handle_redirect_discovery(args: Dict, flow_manager: FlowManager):
    """Handle transition after redirect."""
    logger.debug("Redirecting to discovery page in handle_redirect_discovery")
    await flow_manager.request_navigation("/discovery")
    await flow_manager.set_node("close_call", create_close_node())


# Transition callback mapping
HANDLERS = {
    "collect_name": handle_name_collection,
    "identify_service": handle_service_identification,
    "identify_use_case": handle_use_case_identification,
    "establish_timescales": handle_timescales_establishment,
    "determine_budget": handle_budget_determination,
    "assess_interaction": handle_interaction_assessment,
    "redirect_consultancy": handle_redirect_consultancy,
    "redirect_discovery": handle_redirect_discovery,
}


async def handle_lead_qualification_transition(
    function_name: str, args: Dict, flow_manager: FlowManager
):
    """Handle transitions between lead qualification flow states."""
    logger.debug(f"Processing {function_name} transition with args: {args}")
    await HANDLERS[function_name](args, flow_manager)


class FlowBot(BaseBot):
    """Flow-based bot implementation."""

    def __init__(self, config: AppConfig):
        super().__init__(config)
        self.flow_manager = None

    async def request_navigation(self, path: str):
        """Request the client to navigate to a specific page.

        Args:
            path: The path to navigate to (e.g., "/discovery")
        """
        logger.debug(f"Requesting navigation to {path} in request_navigation")
        await self.rtvi.handle_function_call(
            function_name="navigate",
            tool_call_id=f"nav_{str(uuid.uuid4())}",
            arguments={"path": path},
            llm=self.services.llm,
            context=self.context,
            result_callback=None,
        )

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
        """Implementation-specific pipeline setup."""
        # Initialize flow manager with transition callback
        self.flow_manager = FlowManager(
            task=self.task,
            llm=self.services.llm,
            context_aggregator=self.pipeline_builder.context_aggregator,
            tts=self.services.tts,
            transition_callback=handle_lead_qualification_transition,
        )
        # Store the request_navigation function in the flow manager
        self.flow_manager.request_navigation = self.request_navigation


async def main():
    """Setup and run the lead qualification agent."""
    from utils.run_helpers import run_bot

    await run_bot(FlowBot, AppConfig)


if __name__ == "__main__":
    asyncio.run(main())
