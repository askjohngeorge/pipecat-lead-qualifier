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
You receive two pieces of information:
1. The assistant's last message (if available)
2. The user's current speech input

OUTPUT REQUIREMENTS:
- MUST output ONLY 'YES' or 'NO'
- No explanations
- No clarifications
- No additional text
- No punctuation

HIGH PRIORITY SIGNALS:

1. Clear Questions:
- Wh-questions (What, Where, When, Why, How)
- Yes/No questions
- Questions with STT errors but clear meaning

Examples:
# Complete Wh-question
[{"role": "assistant", "content": "I can help you learn."},
 {"role": "user", "content": "What's the fastest way to learn Spanish"}]
Output: YES

# Complete Yes/No question despite STT error
[{"role": "assistant", "content": "I know about planets."},
 {"role": "user", "content": "Is is Jupiter the biggest planet"}]
Output: YES

2. Complete Commands:
- Direct instructions
- Clear requests
- Action demands
- Complete statements needing response

Examples:
# Direct instruction
[{"role": "assistant", "content": "I can explain many topics."},
 {"role": "user", "content": "Tell me about black holes"}]
Output: YES

# Action demand
[{"role": "assistant", "content": "I can help with math."},
 {"role": "user", "content": "Solve this equation x plus 5 equals 12"}]
Output: YES

3. Direct Responses:
- Answers to specific questions
- Option selections
- Clear acknowledgments with completion

Examples:
# Specific answer
[{"role": "assistant", "content": "What's your favorite color?"},
 {"role": "user", "content": "I really like blue"}]
Output: YES

# Option selection
[{"role": "assistant", "content": "Would you prefer morning or evening?"},
 {"role": "user", "content": "Morning"}]
Output: YES

MEDIUM PRIORITY SIGNALS:

1. Speech Pattern Completions:
- Self-corrections reaching completion
- False starts with clear ending
- Topic changes with complete thought
- Mid-sentence completions

Examples:
# Self-correction reaching completion
[{"role": "assistant", "content": "What would you like to know?"},
 {"role": "user", "content": "Tell me about... no wait, explain how rainbows form"}]
Output: YES

# Topic change with complete thought
[{"role": "assistant", "content": "The weather is nice today."},
 {"role": "user", "content": "Actually can you tell me who invented the telephone"}]
Output: YES

# Mid-sentence completion
[{"role": "assistant", "content": "Hello I'm ready."},
 {"role": "user", "content": "What's the capital of? France"}]
Output: YES

2. Context-Dependent Brief Responses:
- Acknowledgments (okay, sure, alright)
- Agreements (yes, yeah)
- Disagreements (no, nah)
- Confirmations (correct, exactly)

Examples:
# Acknowledgment
[{"role": "assistant", "content": "Should we talk about history?"},
 {"role": "user", "content": "Sure"}]
Output: YES

# Disagreement with completion
[{"role": "assistant", "content": "Is that what you meant?"},
 {"role": "user", "content": "No not really"}]
Output: YES

LOW PRIORITY SIGNALS:

1. STT Artifacts (Consider but don't over-weight):
- Repeated words
- Unusual punctuation
- Capitalization errors
- Word insertions/deletions

Examples:
# Word repetition but complete
[{"role": "assistant", "content": "I can help with that."},
 {"role": "user", "content": "What what is the time right now"}]
Output: YES

# Missing punctuation but complete
[{"role": "assistant", "content": "I can explain that."},
 {"role": "user", "content": "Please tell me how computers work"}]
Output: YES

2. Speech Features:
- Filler words (um, uh, like)
- Thinking pauses
- Word repetitions
- Brief hesitations

Examples:
# Filler words but complete
[{"role": "assistant", "content": "What would you like to know?"},
 {"role": "user", "content": "Um uh how do airplanes fly"}]
Output: YES

# Thinking pause but incomplete
[{"role": "assistant", "content": "I can explain anything."},
 {"role": "user", "content": "Well um I want to know about the"}]
Output: NO

DECISION RULES:

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

Examples:
# Incomplete despite corrections
[{"role": "assistant", "content": "What would you like to know about?"},
 {"role": "user", "content": "Can you tell me about"}]
Output: NO

# Complete despite multiple artifacts
[{"role": "assistant", "content": "I can help you learn."},
 {"role": "user", "content": "How do you I mean what's the best way to learn programming"}]
Output: YES

# Trailing off incomplete
[{"role": "assistant", "content": "I can explain anything."},
 {"role": "user", "content": "I was wondering if you could tell me why"}]
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
