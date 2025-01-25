"""Flow-based bot implementation using the base bot framework."""

import asyncio
from dotenv import load_dotenv

from utils.config import AppConfig
from utils.bot_framework import BaseBot
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat_flows import FlowManager, FlowConfig

# Load environment variables from .env file
load_dotenv()


class FlowBot(BaseBot):
    """Flow-based bot implementation."""

    def __init__(self, config: AppConfig):
        super().__init__(config)
        self.flow_config: FlowConfig = {
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
                                "transition_to": "identify_use_case",
                            },
                        },
                    ],
                },
                "identify_use_case": {
                    "task_messages": [
                        {
                            "role": "system",
                            "content": "Ask about their voice AI needs.",
                        }
                    ],
                    "functions": [
                        {
                            "type": "function",
                            "function": {
                                "name": "identify_use_case",
                                "description": "Record their use case needs",
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
                            "content": "Ask about their desired timeline. Ask for both start date and deadline.",
                        }
                    ],
                    "functions": [
                        {
                            "type": "function",
                            "function": {
                                "name": "establish_timescales",
                                "description": "Record project timeline",
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
                                "description": "Record their budget range",
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
                                "description": "Record their interaction feedback",
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
                                "description": "Record their preferred follow-up method",
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
        self.flow_manager = None

    async def _setup_services_impl(self):
        """Implementation-specific service setup."""
        initial_messages = self.flow_config["nodes"]["rapport_building"][
            "role_messages"
        ]
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

    def _create_pipeline_impl(self):
        """Implementation-specific pipeline setup."""
        # Initialize flow manager
        self.flow_manager = FlowManager(
            task=self.task,
            llm=self.services.llm,
            context_aggregator=self.pipeline_builder.context_aggregator,
            tts=self.services.tts,
            flow_config=self.flow_config,
        )


async def main():
    """Setup and run the lead qualification agent."""
    from utils.run_helpers import run_bot

    await run_bot(FlowBot, AppConfig)


if __name__ == "__main__":
    asyncio.run(main())
