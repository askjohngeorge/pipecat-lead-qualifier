"""Flow-based bot implementation using the base bot framework."""

import asyncio
from typing import Dict
from dotenv import load_dotenv

from utils.config import AppConfig
from utils.bot_framework import BaseBot
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat_flows import FlowManager, FlowConfig, FlowArgs, FlowResult

# Load environment variables from .env file
load_dotenv()


# Node generator functions
def create_rapport_node() -> Dict:
    """Create the initial rapport building node."""
    return {
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
                    "handler": collect_name,
                    "description": "Record the caller's name",
                    "parameters": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                        "required": ["name"],
                    },
                },
            },
        ],
    }


def create_use_case_node(name: str) -> Dict:
    """Create node for identifying use case."""
    return {
        "task_messages": [
            {
                "role": "system",
                "content": f"Ask {name} about their voice AI needs and use case requirements.",
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
                        "properties": {
                            "use_case": {"type": "string"},
                            "complexity": {
                                "type": "string",
                                "enum": ["simple", "moderate", "complex"],
                            },
                        },
                        "required": ["use_case", "complexity"],
                    },
                },
            },
        ],
    }


def create_timescales_node(use_case_complexity: str) -> Dict:
    """Create node for establishing timescales."""
    urgency_prompt = (
        "complex" in use_case_complexity.lower()
        and "Given the complexity, emphasize the need for realistic timelines. "
        or ""
    )
    return {
        "task_messages": [
            {
                "role": "system",
                "content": f"{urgency_prompt}Ask about their desired timeline. Ask for both start date and deadline.",
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
                            "urgency": {
                                "type": "string",
                                "enum": ["low", "medium", "high"],
                            },
                        },
                        "required": ["start_date", "deadline", "urgency"],
                    },
                },
            },
        ],
    }


def create_budget_node(complexity: str, urgency: str) -> Dict:
    """Create node for determining budget based on complexity and urgency."""
    budget_prompt = (
        "complex" in complexity.lower()
        and "high" in urgency.lower()
        and "Given the complexity and urgency, focus on enterprise tier options. "
        or ""
    )
    return {
        "task_messages": [
            {
                "role": "system",
                "content": f"{budget_prompt}Ask about their budget for the voice AI solution. If they're unsure, explain our tiered options.",
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
                        "properties": {
                            "budget_range": {
                                "type": "string",
                                "enum": ["0-5k", "5k-20k", "20k-100k", "100k+"],
                            },
                            "flexibility": {
                                "type": "string",
                                "enum": ["fixed", "somewhat flexible", "very flexible"],
                            },
                        },
                        "required": ["budget_range", "flexibility"],
                    },
                },
            },
        ],
    }


def create_feedback_node() -> Dict:
    """Create node for collecting feedback."""
    return {
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
                        "properties": {
                            "rating": {"type": "integer", "minimum": 1, "maximum": 5},
                            "feedback": {"type": "string"},
                            "sentiment": {
                                "type": "string",
                                "enum": ["positive", "neutral", "negative"],
                            },
                        },
                        "required": ["rating", "sentiment"],
                    },
                },
            },
        ],
    }


def create_call_option_node(sentiment: str) -> Dict:
    """Create node for offering call options based on feedback sentiment."""
    urgency = "immediately" if sentiment == "positive" else "soon"
    return {
        "task_messages": [
            {
                "role": "system",
                "content": f"Offer them the choice between booking a video call with John George {urgency} or receiving follow-up via email.",
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
                            "preference": {
                                "type": "string",
                                "enum": ["video_call", "email"],
                            },
                            "urgency": {
                                "type": "string",
                                "enum": ["asap", "this_week", "next_week"],
                            },
                        },
                        "required": ["preference"],
                    },
                },
            },
        ],
    }


def create_close_node() -> Dict:
    """Create the final node."""
    return {
        "task_messages": [
            {
                "role": "system",
                "content": "Thank them for their time and end the conversation warmly.",
            }
        ],
        "functions": [],
        "post_actions": [{"type": "end_conversation"}],
    }


# Function handlers
async def collect_name(args: FlowArgs) -> FlowResult:
    """Process name collection."""
    return {"name": args["name"]}


async def identify_use_case(args: FlowArgs) -> FlowResult:
    """Process use case identification."""
    return {"use_case": args["use_case"], "complexity": args["complexity"]}


async def establish_timescales(args: FlowArgs) -> FlowResult:
    """Process timeline establishment."""
    return {
        "start_date": args["start_date"],
        "deadline": args["deadline"],
        "urgency": args["urgency"],
    }


async def determine_budget(args: FlowArgs) -> FlowResult:
    """Process budget determination."""
    return {"budget_range": args["budget_range"], "flexibility": args["flexibility"]}


async def assess_feedback(args: FlowArgs) -> FlowResult:
    """Process interaction feedback."""
    return {
        "rating": args["rating"],
        "feedback": args.get("feedback", ""),
        "sentiment": args["sentiment"],
    }


async def offer_call_option(args: FlowArgs) -> FlowResult:
    """Process follow-up preference."""
    return {
        "preference": args["preference"],
        "urgency": args.get("urgency", "this_week"),
    }


# Transition handlers
async def handle_name_collection(args: Dict, flow_manager: FlowManager):
    """Handle transition after name collection."""
    flow_manager.state["name"] = args["name"]
    await flow_manager.set_node("identify_use_case", create_use_case_node(args["name"]))


async def handle_use_case_identification(args: Dict, flow_manager: FlowManager):
    """Handle transition after use case identification."""
    flow_manager.state["use_case"] = args["use_case"]
    flow_manager.state["complexity"] = args["complexity"]
    await flow_manager.set_node(
        "establish_timescales", create_timescales_node(args["complexity"])
    )


async def handle_timescales_establishment(args: Dict, flow_manager: FlowManager):
    """Handle transition after timeline establishment."""
    flow_manager.state.update(args)
    await flow_manager.set_node(
        "determine_budget",
        create_budget_node(flow_manager.state["complexity"], args["urgency"]),
    )


async def handle_budget_determination(args: Dict, flow_manager: FlowManager):
    """Handle transition after budget determination."""
    flow_manager.state.update(args)
    await flow_manager.set_node("assess_feedback", create_feedback_node())


async def handle_feedback_assessment(args: Dict, flow_manager: FlowManager):
    """Handle transition after feedback collection."""
    flow_manager.state.update(args)
    await flow_manager.set_node(
        "offer_call_option", create_call_option_node(args["sentiment"])
    )


async def handle_call_option(args: Dict, flow_manager: FlowManager):
    """Handle transition after call option selection."""
    flow_manager.state.update(args)
    await flow_manager.set_node("close_call", create_close_node())


# Transition callback mapping
HANDLERS = {
    "collect_name": handle_name_collection,
    "identify_use_case": handle_use_case_identification,
    "establish_timescales": handle_timescales_establishment,
    "determine_budget": handle_budget_determination,
    "assess_feedback": handle_feedback_assessment,
    "offer_call_option": handle_call_option,
}


async def handle_lead_qualification_transition(
    function_name: str, args: Dict, flow_manager: FlowManager
):
    """Handle transitions between lead qualification flow states."""
    await HANDLERS[function_name](args, flow_manager)


class FlowBot(BaseBot):
    """Flow-based bot implementation."""

    def __init__(self, config: AppConfig):
        super().__init__(config)
        self.flow_manager = None

    async def _setup_services_impl(self):
        """Implementation-specific service setup."""
        initial_messages = create_rapport_node()["role_messages"]
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
        await self.flow_manager.set_node("rapport", create_rapport_node())

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


async def main():
    """Setup and run the lead qualification agent."""
    from utils.run_helpers import run_bot

    await run_bot(FlowBot, AppConfig)


if __name__ == "__main__":
    asyncio.run(main())
