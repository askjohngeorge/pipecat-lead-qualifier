## Core Concepts

Understanding how Pipecat works: frames, processors, and pipelines.

---

Pipecat uses a pipeline-based architecture to handle real-time AI processing. Let’s look at how this works in practice, then break down the key components.

## Real-time Processing in Action

Consider how a voice assistant processes a user’s question and generates a response:

![Real-time processing pipeline](https://mintlify.s3.us-west-1.amazonaws.com/daily/images/architecture-1.png)

Instead of waiting for complete responses at each step, Pipecat processes data in small units called frames that flow through the pipeline:

1. Speech is transcribed in real-time as the user speaks.
2. Transcription is sent to the LLM as it becomes available.
3. LLM responses are processed as they stream in.
4. Text-to-speech begins generating audio for early sentences while later ones are still being generated.
5. Audio playback starts as soon as the first sentence is ready.
6. LLM context is aggregated and updated continuously and in real-time.

This streaming approach creates natural, responsive interactions.

## Architecture Overview

![Platform architecture](https://mintlify.s3.us-west-1.amazonaws.com/daily/images/architecture-2.png)

The architecture consists of three key components:

### 1. Frames

Frames are containers for data moving through your application. Think of them like packages on a conveyor belt, each containing a specific type of data:

- Audio data from a microphone
- Text from transcription
- LLM responses
- Generated speech audio
- Images or video
- Control signals and system messages

Frames can flow in two directions:

- **Downstream**: Normal processing flow
- **Upstream**: For errors and control signals

### 2. Processors (Services)

Processors are workers along the conveyor belt. Each one:

- Receives frames as inputs
- Processes specific frame types
- Passes through frames it doesn’t handle
- Generates new frames as output

Examples of processors include:

- Speech-to-text processor (Audio → Text)
- LLM processor (Context → Text)
- Text-to-speech processor (Text → Audio)
- Image generation processor (Text → Image URL)
- Logging processor (Monitors frames)

### 3. Pipelines

Pipelines connect processors, creating a path for frames to flow through your application. Pipelines can be:

```python
# Simple linear pipeline
pipeline = Pipeline([
    transport.input(),    # Speech   -> Audio
    transcriber,          # Audio    -> Text
    llm_processor,        # Text     -> Response
    tts_service,          # Response -> Audio
    transport.output()    # Audio    -> Playback
])

# Complex parallel pipeline
pipeline = Pipeline([
    input_source,
    ParallelPipeline([
        [image_processor, image_output],  # Handle images
        [audio_processor, audio_output]  # Handle audio
    ])
])
```

The pipeline also contains the transport, which connects to the real world (e.g., microphone, speakers).

## How It All Works Together

Here’s how these components handle a simple voice interaction:

1. **Input**
   - User speaks into their microphone.
   - Transport converts audio into frames.
   - Frames enter the pipeline.

2. **Processing**
   - Transcription processor converts speech to text frames.
   - LLM processor takes text frames and generates response frames.
   - TTS processor converts response frames to audio frames.
   - Error frames flow upstream if issues occur.
   - System frames bypass normal processing for immediate handling.

3. **Output**
   - Audio frames reach the transport.
   - Transport plays the audio for the user.

This happens continuously and in parallel, creating smooth, real-time interactions.

---

## Use Cases

Common applications you can build with Pipecat.

---

Pipecat is designed for building real-time AI applications that interact through voice, text, images, or video. Here are some common ways developers use Pipecat:

## Voice Assistants

The most straightforward use of Pipecat is building voice-enabled AI agents that can:

- Have natural conversations with users
- Maintain context across multiple exchanges
- Process speech in real-time
- Generate voice responses
- Execute function calls

The [Simple Chatbot](https://github.com/pipecat-ai/pipecat/tree/main/examples/simple-chatbot) is a great example project. This example shows how to build a basic bot and connect to it through different types of client interfaces.

## Multimodal Applications

Pipecat can handle multiple types of input and output simultaneously:

- Process both voice and images
- Generate text and image responses
- Handle video streams
- Combine different AI models

Check out our [Moondream chatbot example](https://github.com/pipecat-ai/pipecat/tree/main/examples/moondream-chatbot) to see multimodal processing in action.

## Complex Conversational Flows

For applications that need structured conversations, like customer service or form filling, you can use [Pipecat Flows](https://github.com/pipecat-ai/pipecat-flows) to:

- Create predefined conversation paths
- Handle dynamic branching based on user input
- Manage conversation state
- Design flows visually using the [Flow Editor](https://flows.pipecat.ai)

Get started by running one of the [Flows examples](https://github.com/pipecat-ai/pipecat-flows/tree/main/examples).

## Real-world Examples

Here are some applications built with Pipecat:

- [Storytelling bot](https://storytelling-chatbot.fly.dev/) that generates and narrates stories
- [Customer intake system](https://www.youtube.com/watch?v=lDevgsp9vn0) for automated form filling
- [Real-time AI conversations](https://demo.dailybots.ai/) using WebRTC
