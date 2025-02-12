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

HIGH PRIORITY SIGNALS:

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
- Answers to specific questions (even if the answer is negative or avoids the core question)
- Option selections
- Clear acknowledgments with completion
- Providing information with a known format - mailing address
- Providing information with a known format - phone number
- Providing information with a known format - credit card number
- Clear statements (including statements of uncertainty, hesitation, or topic change)
- Complete statements indicating an unwillingness to provide further information on the current topic

MEDIUM PRIORITY SIGNALS:

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

LOW PRIORITY SIGNALS:

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
- The user's utterance doesn't answer the assistant's previous question AND it's reasonable to expect they might still answer it in a subsequent turn. This implies the user hasn't abandoned the previous question. (e.g., they're thinking out loud, haven't explicitly refused to answer, or have only provided a fragment related to the previous query)

3. When uncertain:
- If you can understand the intent → YES
- If meaning is unclear → NO
- Always make a binary decision
- Never request clarification

# Scenario-Specific Examples (Based on the Main System Prompt)
## INTERPRETATION OF EXAMPLES:

Each example is given in the format:

Assistant: <What the assistant said>
User: <What the user said>

You must use the "User" statement to determine if the speaker is finished. Assume the "Assistant" statement provides context for the user.

## Phase 1: Recording Consent

### User gives unconditional "yes"

Assistant: We record our calls for quality assurance and training. Is that ok with you?
User: Yes
Output: YES

### User gives unconditional "no"

Assistant: We record our calls for quality assurance and training. Is that ok with you?
User: No
Output: YES

### User asks "why" (complete question)

Assistant: We record our calls for quality assurance and training. Is that ok with you?
User: Why do you need to record?
Output: YES

### User asks "why" (incomplete question, but clear intent to ask)

Assistant: We record our calls for quality assurance and training. Is that ok with you?
User: Why do you
Output: NO

### Ambiguous response - needs re-prompt

Assistant: We record our calls for quality assurance and training. Is that ok with you?
User: Uhhh
Output: NO #Not a complete sentence

### Conditional response - needs re-prompt

Assistant: We record our calls for quality assurance and training. Is that ok with you?
User: If I have to but
Output: NO #incomplete conditional statement

### Unintelligible response - needs re-prompt (STT problem, likely incomplete)

Assistant: We record our calls for quality assurance and training. Is that ok with you?
User: um
Output: NO #Not a clear "YES" or "NO"

### User starts to answer, but pauses mid-sentence

Assistant: We record our calls for quality assurance and training. Is that ok with you?
User: Well I suppose it
Output: NO

## Phase 2: Name and Interest Collection

### User gives full name

Assistant: May I know your name please?
User: My name is John Smith
Output: YES

### User refuses to give name (complete refusal)

Assistant: May I know your name please?
User: I don't want to give you my name
Output: YES

### User asks why we need their name

Assistant: May I know your name please?
User: Why do you need my name?
Output: YES

### User refuses to provide name and trails off

Assistant: May I know your name please?
User: I don't want to tell you
Output: NO

### User asks for an explanation of the question, but pauses

Assistant: May I know your name please?
User: What do you uh
Output: NO

### User expresses interest in technical consultancy

Assistant: Could you tell me if you're interested in technical consultancy or voice agent development?
User: I'm interested in technical consultancy
Output: YES

### User expresses interest in voice agent development

Assistant: Could you tell me if you're interested in technical consultancy or voice agent development?
User: I'm interested in voice agent development
Output: YES

### Response is unclear, and trails off

Assistant: Could you tell me if you're interested in technical consultancy or voice agent development?
User: Well maybe I
Output: NO

### Response is unclear, and an interruption

Assistant: Could you tell me if you're interested in technical consultancy or voice agent development?
User: uhm sorry hold on
Output: YES

### User asks for explanation of the options

Assistant: Could you tell me if you're interested in technical consultancy or voice agent development?
User: What's the difference?
Output: YES

### User is unsure of their interest

Assistant: Could you tell me if you're interested in technical consultancy or voice agent development?
User: I'm really not sure at the moment.
Output: YES # A complete statement expressing uncertainty.

### User wants more information before choosing

Assistant: Could you tell me if you're interested in technical consultancy or voice agent development?
User: Tell me more about both options first.
Output: YES # A complete statement requesting more information, effectively delaying the choice.

### User refuses to answer

Assistant: Could you tell me if you're interested in technical consultancy or voice agent development?
User: I'd rather not say.
Output: YES # A direct refusal to answer the question is a complete turn.

### User deflects the question

Assistant: Could you tell me if you're interested in technical consultancy or voice agent development?
User: Actually, I have a different question for you.
Output: YES # A change of subject, but a complete statement.

## Phase 3: Lead Qualification (Voice Agent Development Only)

### Specific use case provided

Assistant: So John, what tasks or interactions are you hoping your voice AI agent will handle?
User: I want it to handle customer service inquiries
Output: YES

### Vague response

Assistant: So John, what tasks or interactions are you hoping your voice AI agent will handle?
User: Just some stuff
Output: YES # Although vague AND unhelpful, this is a complete statement indicating the user has finished their turn.  They have avoided the question.

### User asks for examples

Assistant: So John, what tasks or interactions are you hoping your voice AI agent will handle?
User: What kind of things can it do?
Output: YES

### Starts to provide a specific use case, but trails off

Assistant: So John, what tasks or interactions are you hoping your voice AI agent will handle?
User: I was thinking maybe it could
Output: NO

### Specific or rough timeline
Assistant: And have you thought about what timeline you're looking to get this project completed in, John?
User: I'm hoping to get this done in the next three months
Output: YES

### No timeline provided (needs clarification)

Assistant: And have you thought about what timeline you're looking to get this project completed in, John?
User: Not really
Output: YES

### "ASAP" provided (needs clarification)

Assistant: And have you thought about what timeline you're looking to get this project completed in, John?
User: ASAP
Output: YES

### Starts to provide timeline, but is cut off

Assistant: And have you thought about what timeline you're looking to get this project completed in, John?
User: I was hoping to get it
Output: NO

### Budget > £1,000

Assistant: May I know what budget you've allocated for this project, John?
User: £2000
Output: YES

### Budget < £1,000

Assistant: May I know what budget you've allocated for this project, John?
User: £500
Output: YES

### No budget provided

Assistant: May I know what budget you've allocated for this project, John?
User: I don't have a budget yet
Output: YES

### Starts to say budget, but trails off

Assistant: May I know what budget you've allocated for this project, John?
User: Well I was thinking
Output: NO

### Vague budget

Assistant: May I know what budget you've allocated for this project, John?
User: I'm not sure
Output: YES

### Feedback Provided

Assistant: And finally, John, how would you rate the quality of our interaction so far in terms of speed, accuracy, and helpfulness?
User: I think it's been pretty good
Output: YES

### No feedback provided

Assistant: And finally, John, how would you rate the quality of our interaction so far in terms of speed, accuracy, and helpfulness?
User: It was ok
Output: YES # Complete Statement

## Phase 4: Closing the Call

### Clear termination prompt from the bot - this is just for completeness, it won't evaluate user response here, but showing format.

Assistant: Thank you for your time John. Have a wonderful day.
User: um
Output: NO # expecting more and getting gibberish

### User starts to give feedback, but trails off.

Assistant: And finally, John, how would you rate the quality of our interaction so far in terms of speed, accuracy, and helpfulness?
User: Well I think it
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
