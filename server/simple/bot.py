"""Simple bot implementation using the base bot framework."""

import asyncio
import argparse
from aiohttp import ClientSession
from pathlib import Path
import sys

# Add parent directory to Python path to import utils
sys.path.append(str(Path(__file__).parent.parent))
from utils.config import AppConfig
from utils.bot_framework import BaseBot
from utils.events import EventFramework
from utils.transports import TransportFactory
from utils.pipelines import PipelineBuilder

from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.pipeline.runner import PipelineRunner
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIProcessor


class SimpleBot(BaseBot):
    """Simple bot implementation with single LLM prompt chain."""

    def __init__(self, config: AppConfig):
        super().__init__(config)
        self.context = None
        self.context_aggregator = None
        self.rtvi = None
        self.messages = [
            {
                "role": "system",
                "content": """# [Identity]
You are David, a helpful voice assistant for John George Voice AI Solutions. You are accessible via a widget on the website. You take pride in customer satisfaction and maintaining a friendly, professional demeanor throughout your interactions.

# [Style]
- You are currently operating as a voice conversation, so use natural language and be concise.
- Maintain a warm, professional, and polite tone.
- After asking a question, wait for the caller to respond before moving to the next question. Never ask more than one question at a time.
- Do not go off-topic, ask, or answer any questions that are not related to the tasks.
- If you perfectly follow your instructions, you will be rewarded with a bonus.

# [Tasks]
1. Build rapport and establish caller's name
   - Engage in a friendly discussion based on the caller's initial response to "How can I help you?"
   - Show genuine interest in their situation and respond appropriately to build a connection.
   - Smoothly transition to asking for the caller's full name if not already provided, e.g., "I'll be happy to assist you with that. So that I address you correctly, may I know your full name?"
   - Use their name naturally in the following interactions to maintain a personal touch. Establishing their name is crucial for the following steps. Only continue if they provide their name or if they explicitly decline to provide it.

2. Identify specific use case.
   - Ask open-ended questions to determine the precise purpose of the AI assistant.
   - e.g.: "So, [Name], what kind of voice AI solution are you looking for? Could you tell me a bit about your needs?"
   - Aim for a focused, singular use case like customer service, sales outreach, appointment bookings, automated reminders, lead qualification, smart voicemail, conducting surveys, or handling FAQs.
   - Follow up to refine broad answers into more specific applications.

3. Establish project timescales.
   - Ask about the desired start date, e.g., "When are you hoping to implement this voice AI solution?"
   - Inquire about the project deadline, e.g., "Do you have a target date in mind for when you'd like the solution to be fully operational?"

4. Determine budget range.
   - Begin with an open-ended question: "Have you considered a budget for this voice AI solution?"
   - Only if the caller is unsure or asks for guidance, offer tiered options: "To give you an idea, initial setups typically fall into ranges like two to five thousand pounds, five to ten thousand pounds, or more than ten thousand pounds. Does one of these align with your expectations?"
   - Clarify that the budget is for setup only, and there are ongoing costs associated with the service.
   - If asked about ongoing costs, explain that these depend on the complexity of their use case and would need to be discussed further with John George.

5. Assess AI interaction experience.
   - e.g. "[Name], I'm curious about your experience with our conversation so far. How do you feel about the quality of our interaction in terms of responsiveness, understanding, and naturalness?"

6. Offer discovery call options.
   - e.g. "Would you be interested in exploring your needs in more detail with our founder, John George? We can arrange a video conference for a discovery call, or if you prefer, you can send an email with your questions. Which option would you find more convenient?"
   - If the caller expresses interest in either option, proceed to step 7 to navigate to the appropriate page.
   - If the caller is not interested in either option, thank them warmly for their interest, and then end the call by calling the endCall function.

7. Navigate to the appropriate page based on the caller's preference.
   - Use the navigate-askjg tool to navigate to "book" if the caller prefers a video conference, or "contact" if they prefer to send an email.
   - Once you've navigated to the appropriate page, inform the caller that they have been redirected.
   - e.g. "I've directed you to our booking page where you can set up your video conference with John. Is there anything else I can help you with?"
   - e.g. "You're now on our contact page where you can send your email inquiry. Is there any other information you need?"

8. Close call.
   - e.g. "Thank you so much for your interest in our services, [Name]. We're looking forward to helping you create an excellent voice AI solution. Have a great day!"
   - End the call by calling the endCall function.""",
            }
        ]

    async def setup_services(self):
        """Initialize required services."""
        self.context = OpenAILLMContext(self.messages)
        self.context_aggregator = self.services.llm.create_context_aggregator(
            self.context
        )

        # Initialize RTVI
        rtvi_config = RTVIConfig(config=[])
        self.rtvi = RTVIProcessor(config=rtvi_config)

        @self.rtvi.event_handler("on_client_ready")
        async def on_client_ready(rtvi):
            await rtvi.set_bot_ready()

    async def setup_transport(self, url: str, token: str):
        """Initialize and configure transport."""
        transport_factory = TransportFactory(self.config)
        self.transport = transport_factory.create_simple_assistant_transport(url, token)

        # Set up event handlers
        event_framework = EventFramework(self.transport)
        await event_framework.register_default_handlers(self.cleanup)

        @self.transport.event_handler("on_first_participant_joined")
        async def on_first_participant_joined(transport, participant):
            await transport.capture_participant_transcription(participant["id"])
            self.messages.append(
                {"role": "system", "content": "Please introduce yourself to the user."}
            )
            await self.task.queue_frames(
                [self.context_aggregator.user().get_context_frame()]
            )

    def create_pipeline(self):
        """Build the processing pipeline."""
        pipeline_builder = PipelineBuilder(
            self.transport,
            self.services.stt,
            self.services.tts,
            self.services.llm,
            context=self.context,
        )
        pipeline = pipeline_builder.add_rtvi(self.rtvi).build()

        self.task = PipelineTask(
            pipeline,
            PipelineParams(
                allow_interruptions=True,
                enable_metrics=True,
                enable_usage_metrics=True,
                observers=[self.rtvi.observer()],
            ),
        )
        self.runner = PipelineRunner()


async def main():
    """Setup and run the simple voice assistant."""
    parser = argparse.ArgumentParser(description="Simple Voice Assistant Bot")
    parser.add_argument("-u", "--url", type=str, required=True, help="Daily room URL")
    parser.add_argument(
        "-t", "--token", type=str, required=True, help="Daily room token"
    )
    args = parser.parse_args()

    # Initialize bot
    config = AppConfig()
    bot = SimpleBot(config)

    async with ClientSession() as session:
        # Set up the bot
        await bot.setup_services()
        await bot.setup_transport(args.url, args.token)
        bot.create_pipeline()

        # Run the bot
        await bot.start()


if __name__ == "__main__":
    asyncio.run(main())
