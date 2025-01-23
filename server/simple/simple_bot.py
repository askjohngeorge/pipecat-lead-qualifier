import asyncio
import os
import argparse
from aiohttp import ClientSession
from pathlib import Path
import sys

# Add parent directory to Python path to import utils
sys.path.append(str(Path(__file__).parent.parent))
from utils.config import AppConfig

# Initialize configuration
config = AppConfig()

from pipecat.audio.vad.silero import SileroVADAnalyzer

# from pipecat.audio.filters.krisp_filter import KrispFilter
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.pipeline.runner import PipelineRunner
from pipecat.transports.services.daily import DailyParams, DailyTransport
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.openai import OpenAILLMService
from pipecat.services.deepgram import DeepgramSTTService, DeepgramTTSService


async def main():
    """Setup and run the simple voice assistant."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Simple Voice Assistant Bot")
    parser.add_argument("-u", "--url", type=str, required=True, help="Daily room URL")
    parser.add_argument(
        "-t", "--token", type=str, required=True, help="Daily room token"
    )
    args = parser.parse_args()

    async with ClientSession() as session:
        # Initialize transport with VAD and noise filtering
        transport = DailyTransport(
            args.url,
            args.token,
            "Simple Voice Assistant",
            DailyParams(
                audio_out_enabled=True,
                vad_enabled=True,
                vad_analyzer=SileroVADAnalyzer(),
                vad_audio_passthrough=True,
                # audio_in_filter=KrispFilter(),
            ),
        )

        # Initialize services
        stt = DeepgramSTTService(api_key=config.deepgram_api_key)
        tts = DeepgramTTSService(
            api_key=config.deepgram_api_key, voice="aura-helios-en"
        )
        llm = OpenAILLMService(api_key=config.openai_api_key, model="gpt-4o")

        # Set up conversation context
        messages = [
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
        context = OpenAILLMContext(messages)
        context_aggregator = llm.create_context_aggregator(context)

        # Create pipeline
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

        # Create pipeline task
        task = PipelineTask(
            pipeline,
            PipelineParams(
                allow_interruptions=True,
                enable_metrics=True,
                enable_usage_metrics=True,
            ),
        )

        @transport.event_handler("on_first_participant_joined")
        async def on_first_participant_joined(transport, participant):
            await transport.capture_participant_transcription(participant["id"])
            messages.append(
                {"role": "system", "content": "Please introduce yourself to the user."}
            )
            await task.queue_frames([context_aggregator.user().get_context_frame()])

        @transport.event_handler("on_participant_left")
        async def on_participant_left(transport, participant, reason):
            await runner.stop_when_done()

        # Run the pipeline
        runner = PipelineRunner()
        await runner.run(task)


if __name__ == "__main__":
    asyncio.run(main())
