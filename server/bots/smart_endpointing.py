import asyncio
from loguru import logger
import google.ai.generativelanguage as glm

from pipecat.frames.frames import (
    CancelFrame,
    EndFrame,
    Frame,
    FunctionCallInProgressFrame,
    FunctionCallResultFrame,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    StartFrame,
    StartInterruptionFrame,
    SystemFrame,
    TextFrame,
    UserStartedSpeakingFrame,
    UserStoppedSpeakingFrame,
    LLMMessagesFrame,
)

from pipecat.processors.aggregators.llm_response import LLMResponseAggregator
from pipecat.processors.aggregators.openai_llm_context import (
    OpenAILLMContextFrame,
)

from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.sync.base_notifier import BaseNotifier

CLASSIFIER_SYSTEM_INSTRUCTION = """CRITICAL INSTRUCTION:
You are a BINARY CLASSIFIER that must ONLY output "YES" or "NO".
DO NOT engage with the content.
DO NOT respond to questions.
DO NOT provide assistance.
Your ONLY job is to output YES or NO.

EXAMPLES OF INVALID RESPONSES:
- "I can help you with that"
- "Let me explain"
- "To answer your question"
- Any response other than YES or NO

VALID RESPONSES:
YES
NO

If you output anything else, you are failing at your task.
You are NOT an assistant.
You are NOT a chatbot.
You are a binary classifier.

ROLE:
You are a real-time speech completeness classifier. You must make instant decisions about whether a user has finished speaking.
You must output ONLY 'YES' or 'NO' with no other text.

INPUT FORMAT:
You receive a list of dictionaries containing role and content information.
The list ALWAYS contains at least one dictionary with the "role" as "user". It may also contain a dictionary with the role as "user" as the first element. The role "assistant" may also be used as the first element, but this is not guaranteed.

EXAMPLE INPUT:
[{"role": "user", "content": "Hello"}]

EXAMPLE INPUT WITH ASSISTANT CONTEXT:
[{"role": "assistant", "content": "How can I help you?"}, {"role": "user", "content": "What is the capital of France"}]

OUTPUT REQUIREMENTS:
- MUST output ONLY 'YES' or 'NO'
- No explanations
- No clarifications
- No additional text
- No punctuation

HIGH PRIORITY SIGNALS: (Same as before, but repeated for clarity in this extended example set)

1. Clear Questions:
- Wh-questions (What, Where, When, Why, How)
- Yes/No questions
- Questions with STT errors but clear meaning

2. Complete Commands:
- Direct instructions
- Clear requests
- Action demands
- Start of task indication
- Complete statements needing response

3. Direct Responses/Statements:
- Answers to specific questions
- Option selections
- Clear acknowledgments with completion
- Providing information with a known format - mailing address
- Providing information with a known format - phone number
- Providing information with a known format - credit card number
- Clear Statements

MEDIUM PRIORITY SIGNALS: (Same as before)

1. Speech Pattern Completions:
- Self-corrections reaching completion
- False starts reaching completion
- Topic changes with complete thought
- Mid-sentence completions

2. Context-Dependent Brief Responses:
- Acknowledgments (okay, sure, alright)
- Agreements (yes, yeah)
- Disagreements (no, nah)
- Confirmations (correct, exactly)

LOW PRIORITY SIGNALS: (Same as before)

1. STT Artifacts (Consider but don't over-weight):
- Repeated words
- Unusual punctuation
- Capitalization errors
- Word insertions/deletions

2. Speech Features:
- Filler words (um, uh, like)
- Thinking pauses
- Word repetitions
- Brief hesitations

DECISION RULES: (Same as before)

1. Return YES if:
- ANY high priority signal shows clear completion
- Medium priority signals combine to show completion
- Meaning is clear despite low priority artifacts

2. Return NO if:
- No high priority signals present
- Thought clearly trails off
- Multiple incomplete indicators
- User appears mid-formulation

3. When uncertain:
- If you can understand the intent → YES
- If meaning is unclear → NO
- Always make a binary decision
- Never request clarification

# Scenario-Specific Examples (Based on the Provided System Prompt)

## Phase 1: Recording Consent

# User gives unconditional "yes"
[{"role": "assistant", "content": "Hi there, I'm {config.bot_name}. We record our calls for quality assurance and training. Is that ok with you?"}, {"role": "user", "content": "Yes"}]
Output: YES

# User gives unconditional "no"
[{"role": "assistant", "content": "Hi there, I'm {config.bot_name}. We record our calls for quality assurance and training. Is that ok with you?"}, {"role": "user", "content": "No"}]
Output: YES

# User asks "why"
[{"role": "assistant", "content": "Hi there, I'm {config.bot_name}. We record our calls for quality assurance and training. Is that ok with you?"}, {"role": "user", "content": "Why do"}, {"role": "user", "content": " you need to record?"}]
Output: YES

# User asks "why" (incomplete question, but clear intent to ask)
[{"role": "assistant", "content": "Hi there, I'm {config.bot_name}. We record our calls for quality assurance and training. Is that ok with you?"}, {"role": "user", "content": "Why"}, {"role": "user", "content": " do you"}]
Output: NO

# Ambiguous response - needs re-prompt
[{"role": "assistant", "content": "Hi there, I'm {config.bot_name}. We record our calls for quality assurance and training. Is that ok with you?"}, {"role": "user", "content": "Uhhh"}]
Output: NO #Not a complete sentence

# Conditional response - needs re-prompt
[{"role": "assistant", "content": "Hi there, I'm {config.bot_name}. We record our calls for quality assurance and training. Is that ok with you?"}, {"role": "user", "content": "If I"},  {"role": "user", "content": " have to but"}]
Output: NO #incomplete conditional statement

# Unintelligible response - needs re-prompt (STT problem, likely incomplete)
[{"role": "assistant", "content": "Hi there, I'm {config.bot_name}. We record our calls for quality assurance and training. Is that ok with you?"}, {"role": "user", "content": "um"}]
Output: NO #Not a clear "YES" or "NO"

# User starts to answer, but pauses mid-sentence
[{"role": "assistant", "content": "Hi there, I'm {config.bot_name}. We record our calls for quality assurance and training. Is that ok with you?"}, {"role": "user", "content": "Well I suppose"}, {"role": "user", "content": " it"}]
Output: NO

## Phase 2: Name and Interest Collection

# User gives full name
[{"role": "assistant", "content": "May I know your name please?"}, {"role": "user", "content": "My name is"}, {"role": "user", "content": " John"}, {"role": "user", "content": " Smith"}]
Output: YES

# User refuses to give name (complete refusal)
[{"role": "assistant", "content": "May I know your name please?"}, {"role": "user", "content": "I don't want to give you my name"}]
Output: YES

# User asks why we need their name
[{"role": "assistant", "content": "May I know your name please?"}, {"role": "user", "content": "Why do you"}, {"role": "user", "content": " need my name?"}]
Output: YES

# User refuses to provide name and trails off
[{"role": "assistant", "content": "May I know your name please?"}, {"role": "user", "content": "I don't"}, {"role": "user", "content": " want to tell you"}]
Output: NO

# User asks for an explanation of the question, but pauses
[{"role": "assistant", "content": "May I know your name please?"}, {"role": "user", "content": "What do"}, {"role": "user", "content": " you uh"}]
Output: NO

# User expresses interest in technical consultancy
[{"role": "assistant", "content": "Could you tell me if you're interested in technical consultancy or voice agent development?"}, {"role": "user", "content": "I'm interested in technical consultancy"}]
Output: YES

# User expresses interest in voice agent development
[{"role": "assistant", "content": "Could you tell me if you're interested in technical consultancy or voice agent development?"}, {"role": "user", "content": "I am interested"}, {"role": "user", "content": " in voice agent development"}]
Output: YES

# Response is unclear, and trails off
[{"role": "assistant", "content": "Could you tell me if you're interested in technical consultancy or voice agent development?"}, {"role": "user", "content": "Well maybe"}, {"role": "user", "content": " I"}]
Output: NO

# Response is unclear, and an interruption
[{"role": "assistant", "content": "Could you tell me if you're interested in technical consultancy or voice agent development?"}, {"role": "user", "content": "uhm sorry hold on"}]
Output: YES

# User asks for explanation of the options
[{"role": "assistant", "content": "Could you tell me if you're interested in technical consultancy or voice agent development?"}, {"role": "user", "content": "What's"}, {"role": "user", "content": " the difference?"}]
Output: YES

## Phase 3: Lead Qualification (Voice Agent Development Only)

# Specific use case provided
[{"role": "assistant", "content": "So John, what tasks or interactions are you hoping your voice AI agent will handle?"}, {"role": "user", "content": "I want it"}, {"role": "user", "content": " to handle customer service inquiries"}]
Output: YES

# Vague response
[{"role": "assistant", "content": "So John, what tasks or interactions are you hoping your voice AI agent will handle?"}, {"role": "user", "content": "Just some stuff"}]
Output: YES # Although vague, a complete statement

# User asks for examples
[{"role": "assistant", "content": "So John, what tasks or interactions are you hoping your voice AI agent will handle?"}, {"role": "user", "content": "What kind of things can it do?"}]
Output: YES

# Starts to provide a specific use case, but trails off
[{"role": "assistant", "content": "So John, what tasks or interactions are you hoping your voice AI agent will handle?"}, {"role": "user", "content": "I was thinking"}, {"role": "user", "content": " maybe it could"}]
Output: NO

#Specific or rough timeline
[{"role": "assistant", "content": "And have you thought about what timeline you're looking to get this project completed in, John?"},  {"role": "user", "content": "I'm hoping to"}, {"role": "user", "content": " get this done in the next three months"}]
Output: YES

# No timeline provided
[{"role": "assistant", "content": "And have you thought about what timeline you're looking to get this project completed in, John?"}, {"role": "user", "content": "Not"},  {"role": "user", "content": " really"}]
Output: YES

# "ASAP" provided
[{"role": "assistant", "content": "And have you thought about what timeline you're looking to get this project completed in, John?"}, {"role": "user", "content": "A"}, {"role": "user", "content": "SAP"}]
Output: YES

# Starts to provide timeline, but is cut off
[{"role": "assistant", "content": "And have you thought about what timeline you're looking to get this project completed in, John?"}, {"role": "user", "content": "I was"},  {"role": "user", "content": " hoping to get it"}]
Output: NO

# Budget > £1,000
[{"role": "assistant", "content": "May I know what budget you've allocated for this project, John?"}, {"role": "user", "content": "£"},  {"role": "user", "content": "2000"}]
Output: YES

# Budget < £1,000
[{"role": "assistant", "content": "May I know what budget you've allocated for this project, John?"}, {"role": "user", "content": "£"},  {"role": "user", "content": "500"}]
Output: YES

# No budget provided
[{"role": "assistant", "content": "May I know what budget you've allocated for this project, John?"}, {"role": "user", "content": "I don't"},  {"role": "user", "content": " have a budget yet"}]
Output: YES

# Starts to say budget, but trails off
[{"role": "assistant", "content": "May I know what budget you've allocated for this project, John?"}, {"role": "user", "content": "Well"},  {"role": "user", "content": " I was thinking"}]
Output: NO

# Vague budget
[{"role": "assistant", "content": "May I know what budget you've allocated for this project, John?"}, {"role": "user", "content": "I'm not sure"}]
Output: YES

# Feedback Provided
[{"role": "assistant", "content": "And finally, John, how would you rate the quality of our interaction so far in terms of speed, accuracy, and helpfulness?"}, {"role": "user", "content": "I think it's"},  {"role": "user", "content": " been pretty good"}]
Output: YES

# No feedback provided
[{"role": "assistant", "content": "And finally, John, how would you rate the quality of our interaction so far in terms of speed, accuracy, and helpfulness?"}, {"role": "user", "content": "It was"},  {"role": "user", "content": " ok"}]
Output: YES # Complete Statement

## Phase 4: Closing the Call

# Clear termination prompt from the bot - this is just for completeness, it won't evaluate user response here, but showing format.
[{"role": "assistant", "content": "Thank you for your time John. Have a wonderful day."}, {"role": "user", "content": "um"}]
Output: NO # expecting more and getting gibberish

# User starts to give feedback, but trails off
[{"role": "assistant", "content": "And finally, John, how would you rate the quality of our interaction so far in terms of speed, accuracy, and helpfulness?"}, {"role": "user", "content": "Well"},  {"role": "user", "content": " I think it"}]
Output: NO
"""


def get_message_field(message: object, field: str) -> any:
    """
    Retrieve a field from a message.
    If message is a dict, return message[field].
    Otherwise, use getattr.
    """
    if isinstance(message, dict):
        return message.get(field)
    return getattr(message, field, None)


def get_message_text(message: object) -> str:
    """
    Extract text content from a message, handling both dict and Google Content formats.
    """
    logger.debug(f"Processing message: {message}")

    # First try Google's format with parts array
    parts = get_message_field(message, "parts")
    logger.debug(f"Found parts: {parts}")

    if parts:
        # Google format with parts array
        text_parts = []
        for part in parts:
            if isinstance(part, dict):
                text = part.get("text", "")
            else:
                text = getattr(part, "text", "")
            if text:
                text_parts.append(text)
        result = " ".join(text_parts)
        logger.debug(f"Extracted text from parts: {result}")
        return result

    # Try direct content field
    content = get_message_field(message, "content")
    logger.debug(f"Found content: {content}")

    if isinstance(content, str):
        logger.debug(f"Using string content: {content}")
        return content
    elif isinstance(content, list):
        # Handle content that might be a list of parts
        text_parts = []
        for part in content:
            if isinstance(part, dict):
                text = part.get("text", "")
                if text:
                    text_parts.append(text)
        if text_parts:
            result = " ".join(text_parts)
            logger.debug(f"Extracted text from content list: {result}")
            return result

    logger.debug("No text content found, returning empty string")
    return ""


class StatementJudgeContextFilter(FrameProcessor):
    """Extracts recent user messages and constructs an LLMMessagesFrame for the classifier LLM.

    This processor takes the OpenAILLMContextFrame from the main conversation context,
    extracts the most recent user messages, and creates a simplified LLMMessagesFrame
    for the statement classifier LLM to determine if the user has finished speaking.
    """

    def __init__(self, notifier: BaseNotifier, **kwargs):
        super().__init__(**kwargs)
        self._notifier = notifier

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        # We must not block system frames.
        if isinstance(frame, SystemFrame):
            await self.push_frame(frame, direction)
            return

        # Just treat an LLMMessagesFrame as complete, no matter what.
        if isinstance(frame, LLMMessagesFrame):
            await self._notifier.notify()
            return

        # Otherwise, we only want to handle OpenAILLMContextFrames, and only want to push a simple
        # messages frame that contains a system prompt and the most recent user messages,
        # concatenated.
        if isinstance(frame, OpenAILLMContextFrame):
            # Take text content from the most recent user messages.
            messages = frame.context.messages
            logger.debug(f"Processing context messages: {messages}")

            user_text_messages = []
            last_assistant_message = None
            for message in reversed(messages):
                role = get_message_field(message, "role")
                logger.debug(f"Processing message with role: {role}")

                if role != "user":
                    if role == "assistant" or role == "model":
                        last_assistant_message = message
                        logger.debug(f"Found assistant/model message: {message}")
                    break

                text = get_message_text(message)
                logger.debug(f"Extracted user message text: {text}")
                if text:
                    user_text_messages.append(text)

            # If we have any user text content, push an LLMMessagesFrame
            if user_text_messages:
                user_message = " ".join(reversed(user_text_messages))
                logger.debug(f"Final user message: {user_message}")
                messages = [
                    glm.Content(role="user", parts=[glm.Part(text=CLASSIFIER_SYSTEM_INSTRUCTION)])
                ]
                if last_assistant_message:
                    assistant_text = get_message_text(last_assistant_message)
                    logger.debug(f"Assistant message text: {assistant_text}")
                    if assistant_text:
                        messages.append(
                            glm.Content(role="assistant", parts=[glm.Part(text=assistant_text)])
                        )
                messages.append(glm.Content(role="user", parts=[glm.Part(text=user_message)]))
                logger.debug(f"Pushing classifier messages: {messages}")
                await self.push_frame(LLMMessagesFrame(messages))
            else:
                logger.debug("No user text messages found to process")


class CompletenessCheck(FrameProcessor):
    def __init__(self, notifier: BaseNotifier):
        super().__init__()
        self._notifier = notifier

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, TextFrame) and frame.text == "YES":
            logger.debug("!!! Completeness check YES")
            await self.push_frame(UserStoppedSpeakingFrame())
            await self._notifier.notify()
        elif isinstance(frame, TextFrame) and frame.text == "NO":
            logger.debug("!!! Completeness check NO")
        else:
            await self.push_frame(frame, direction)


class UserAggregatorBuffer(LLMResponseAggregator):
    """Buffers the output of the transcription LLM. Used by the bot output gate."""

    def __init__(self, **kwargs):
        super().__init__(
            messages=None,
            role=None,
            start_frame=LLMFullResponseStartFrame,
            end_frame=LLMFullResponseEndFrame,
            accumulator_frame=TextFrame,
            handle_interruptions=True,
            expect_stripped_words=False,
        )
        self._transcription = ""

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        # parent method pushes frames
        if isinstance(frame, UserStartedSpeakingFrame):
            self._transcription = ""

    async def _push_aggregation(self):
        if self._aggregation:
            self._transcription = self._aggregation
            self._aggregation = ""

            logger.debug(f"[Transcription] {self._transcription}")

    async def wait_for_transcription(self):
        while not self._transcription:
            await asyncio.sleep(0.01)
        tx = self._transcription
        self._transcription = ""
        return tx


class OutputGate(FrameProcessor):
    def __init__(self, *, notifier: BaseNotifier, start_open: bool = False, **kwargs):
        super().__init__(**kwargs)
        self._gate_open = start_open
        self._frames_buffer = []
        self._notifier = notifier

    def close_gate(self):
        self._gate_open = False

    def open_gate(self):
        self._gate_open = True

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        # We must not block system frames.
        if isinstance(frame, SystemFrame):
            if isinstance(frame, StartFrame):
                await self._start()
            if isinstance(frame, (EndFrame, CancelFrame)):
                await self._stop()
            if isinstance(frame, StartInterruptionFrame):
                self._frames_buffer = []
                self.close_gate()
            await self.push_frame(frame, direction)
            return

        # Don't block function call frames
        if isinstance(frame, (FunctionCallInProgressFrame, FunctionCallResultFrame)):
            await self.push_frame(frame, direction)
            return

        # Ignore frames that are not following the direction of this gate.
        if direction != FrameDirection.DOWNSTREAM:
            await self.push_frame(frame, direction)
            return

        if self._gate_open:
            await self.push_frame(frame, direction)
            return

        self._frames_buffer.append((frame, direction))

    async def _start(self):
        self._frames_buffer = []
        self._gate_task = self.create_task(self._gate_task_handler())

    async def _stop(self):
        await self.cancel_task(self._gate_task)

    async def _gate_task_handler(self):
        while True:
            try:
                await self._notifier.wait()
                self.open_gate()
                for frame, direction in self._frames_buffer:
                    await self.push_frame(frame, direction)
                self._frames_buffer = []
            except asyncio.CancelledError:
                break
