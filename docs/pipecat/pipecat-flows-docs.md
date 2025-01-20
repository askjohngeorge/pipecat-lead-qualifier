# Pipecat Flows

Pipecat Flows provides a framework for building structured conversations in your AI applications. It enables you to create both predefined conversation paths and dynamically generated flows while handling the complexities of state management and LLM interactions.

The framework consists of:
- A Python module for building conversation flows with Pipecat
- A visual editor for designing and exporting flow configurations

## Key Concepts

- **Nodes**: Represent conversation states with specific messages and available functions
- **Messages**: Set the role and tasks for each node
- **Functions**: Define actions and transitions (Node functions for operations, Edge functions for transitions)
- **Actions**: Execute operations during state transitions (pre/post actions)
- **State Management**: Handle conversation state and data persistence

## Example Flows

### Movie Explorer (Static)
A static flow demonstrating movie exploration using OpenAI. Shows real API integration with TMDB, structured data collection, and state management.

### Insurance Policy (Dynamic)
A dynamic flow using Google Gemini that adapts policy recommendations based on user responses. Demonstrates runtime node creation and conditional paths.

> **Note**: These examples are fully functional and can be run locally. Make sure you have the required dependencies installed and API keys configured.

## When to Use Static vs Dynamic Flows

**Static Flows** are ideal when:
- Conversation structure is known upfront
- Paths follow predefined patterns
- Flow can be fully configured in advance
- Example: Customer service scripts, intake forms

**Dynamic Flows** are better when:
- Paths depend on external data
- Flow structure needs runtime modification
- Complex decision trees are involved
- Example: Personalized recommendations, adaptive workflows

# Installation

If you're already using Pipecat:

```bash
pip install pipecat-ai-flows
```

If you're starting fresh:

```bash
# Basic installation
pip install pipecat-ai-flows

# Install Pipecat with specific LLM provider options:
pip install "pipecat-ai[daily,openai,deepgram]"     # For OpenAI
pip install "pipecat-ai[daily,anthropic,deepgram]"  # For Anthropic
pip install "pipecat-ai[daily,google,deepgram]"     # For Google
```

💡 Want to design your flows visually? Try the [online Flow Editor](https://flows.pipecat.ai)

# Core Concepts

## Designing Conversation Flows

Functions in Pipecat Flows serve two key purposes:
- interfacing with external systems and APIs
- advancing the conversation to the next node

### Function Handlers

When you need to collect data, validate input, or retrieve information, add a handler to your function. These handlers are async functions that execute when the LLM calls the function, allowing you to interact with databases, APIs, or other external services:

```python
# Example function handler
async def check_availability(args: FlowArgs) -> FlowResult:
    """Check restaurant availability for the requested time."""
    date = args["date"]
    time = args["time"]
    party_size = args["party_size"]

    # Interface with reservation system
    available = await reservation_system.check_availability(date, time, party_size)
    return {"status": "success", "available": available}
```

### Transitioning Between Nodes

To advance the conversation, Pipecat Flows offers two approaches based on your flow type:

For static flows, use the `transition_to` property to specify the next node:

```python
{
    "type": "function",
    "function": {
        "name": "confirm_reservation",
        "handler": save_reservation,  # Process the reservation
        "parameters": {...},
        "transition_to": "send_confirmation"  # Move to confirmation node
    }
}
```

For dynamic flows, use a transition callback to determine the next node at runtime:

```python
async def handle_transitions(function_name: str, args: Dict, flow_manager):
    if function_name == "check_availability":
        if args["available"]:
            await flow_manager.set_node("collect_details", create_details_node())
        else:
            await flow_manager.set_node("suggest_alternatives", create_alternatives_node())
```

You can combine both approaches: use handlers to process data and transitions to advance the conversation, creating flows that are both functional and conversational.

## Node Structure

Each node in your flow represents a conversation state and consists of three main components:

### Messages

Nodes use two types of messages to control the conversation:

1. **Role Messages**: Define the bot's personality or role (optional)

```python
"role_messages": [
    {
        "role": "system",
        "content": "You are a friendly pizza ordering assistant. Keep responses casual and upbeat."
    }
]
```

2. **Task Messages**: Define what the bot should do in the current node

```python
"task_messages": [
    {
        "role": "system",
        "content": "Ask the customer which pizza size they'd like: small, medium, or large."
    }
]
```

Role messages are typically defined in your initial node and inherited by subsequent nodes, while task messages are specific to each node's purpose.

### Functions

Functions in Pipecat Flows can:
1. Process data (using `handler`)
2. Create transitions (using `transition_to`)
3. Do both simultaneously

This leads to two conceptual types of functions:

#### Node Functions

Functions that process data within a state. They typically:
- Have a `handler` to interface with external systems or APIs
- May optionally include `transition_to` to move to another state after processing

```python
from pipecat_flows import FlowArgs, FlowResult

async def select_size(args: FlowArgs) -> FlowResult:
    """Process pizza size selection."""
    size = args["size"]
    return {
        "status": "success",
        "size": size
    }

# Node function configuration
{
    "type": "function",
    "function": {
        "name": "select_size",
        "handler": select_size,           # Required: Processes the selection
        "description": "Select pizza size",
        "parameters": {
            "type": "object",
            "properties": {
                "size": {"type": "string", "enum": ["small", "medium", "large"]}
            }
        },
        "transition_to": "toppings"       # Optional: Move to toppings selection
    }
}
```

#### Edge Functions

Functions that create transitions between states. They:
- Must have `transition_to` to specify the next state
- May optionally include a `handler` to perform operations during transition

```python
# Edge function configuration
{
    "type": "function",
    "function": {
        "name": "next_step",
        "description": "Move to next state",
        "parameters": {"type": "object", "properties": {}},
        "handler": select_size,        # Optional: Process data during transition
        "transition_to": "target_node" # Required: Specify next state
    }
}
```

A function's behavior is determined by its properties:
- `handler` only: Process data, stay in current state
- `transition_to` only: Pure transition to next state
- Both: Process data, then transition

### Actions

Actions are operations that execute during state transitions, with two distinct timing options:

#### Pre-Actions

Execute before LLM inference. Useful for:
- Providing immediate feedback while waiting for LLM responses
- Bridging gaps during longer function calls
- Setting up state or context

```python
"pre_actions": [
    {
        "type": "tts_say",
        "text": "Hold on a moment..."  # Immediate feedback during processing
    }
],
```

> **Tip**: Avoid mixing `tts_say` actions with chat completions as this may result in a conversation flow that feels unnatural. `tts_say` are best used as filler words when the LLM will take time to generate an completion.

#### Post-Actions

Execute after LLM inference completes. Useful for:
- Cleanup operations
- State finalization
- Ensuring proper sequence of operations

```python
"post_actions": [
    {
        "type": "end_conversation"  # Ensures TTS completes before ending
    }
]
```

#### Timing Considerations

- **Pre-actions**: Execute immediately, before any LLM processing begins
- **LLM Inference**: Processes the node's messages and functions
- **Post-actions**: Execute only after LLM processing and TTS completion

For example, when using `end_conversation` as a post-action, the sequence is:
1. LLM generates response
2. TTS speaks the response
3. End conversation action executes

This ordering ensures proper completion of all operations.

## State Management

The `state` variable in FlowManager is a shared dictionary that persists throughout the conversation. Think of it as a conversation memory that lets you:
- Store user information
- Track conversation progress
- Share data between nodes
- Inform decision-making

Here's a practical example of a pizza ordering flow:

```python
# Store user choices as they're made
async def select_size(args: FlowArgs) -> FlowResult:
    """Handle pizza size selection."""
    size = args["size"]

    # Initialize order in state if it doesn't exist
    if "order" not in flow_manager.state:
        flow_manager.state["order"] = {}

    # Store the selection
    flow_manager.state["order"]["size"] = size

    return {"status": "success", "size": size}

async def select_toppings(args: FlowArgs) -> FlowResult:
    """Handle topping selection."""
    topping = args["topping"]

    # Get existing order and toppings
    order = flow_manager.state.get("order", {})
    toppings = order.get("toppings", [])

    # Add new topping
    toppings.append(topping)
    order["toppings"] = toppings
    flow_manager.state["order"] = order

    return {"status": "success", "toppings": toppings}

async def finalize_order(args: FlowArgs) -> FlowResult:
    """Process the complete order."""
    order = flow_manager.state.get("order", {})

    # Validate order has required information
    if "size" not in order:
        return {"status": "error", "error": "No size selected"}

    # Calculate price based on stored selections
    size = order["size"]
    toppings = order.get("toppings", [])
    price = calculate_price(size, len(toppings))

    return {
        "status": "success",
        "summary": f"Ordered: {size} pizza with {', '.join(toppings)}",
        "price": price
    }
```

In this example:
1. `select_size` initializes the order and stores the size
2. `select_toppings` builds a list of toppings
3. `finalize_order` uses the stored information to process the complete order

The state variable makes it easy to:
- Build up information across multiple interactions
- Access previous choices when needed
- Validate the complete order
- Calculate final results

This is particularly useful when information needs to be collected across multiple conversation turns or when later decisions depend on earlier choices.

## LLM Provider Support

Pipecat Flows automatically handles format differences between LLM providers:

### OpenAI Format

```python
"functions": [{
    "type": "function",
    "function": {
        "name": "function_name",
        "description": "description",
        "parameters": {...}
    }
}]
```

### Anthropic Format

```python
"functions": [{
    "name": "function_name",
    "description": "description",
    "input_schema": {...}
}]
```

### Google (Gemini) Format

```python
"functions": [{
    "function_declarations": [{
        "name": "function_name",
        "description": "description",
        "parameters": {...}
    }]
}]
```

> **Note**: You don't need to handle these differences manually - Pipecat Flows adapts your configuration to the correct format based on your LLM provider.

# Implementation Approaches

## Static Flows

Static flows use a configuration-driven approach where the entire conversation structure is defined upfront.

### Basic Setup

```python
from pipecat_flows import FlowManager

# Define flow configuration
flow_config = {
    "initial_node": "greeting",
    "nodes": {
        "greeting": {
            "role_messages": [...],
            "task_messages": [...],
            "functions": [...]
        }
    }
}

# Initialize flow manager with static configuration
flow_manager = FlowManager(task=task, llm=llm, tts=tts, flow_config=flow_config)

@transport.event_handler("on_first_participant_joined")
async def on_first_participant_joined(transport, participant):
    await transport.capture_participant_transcription(participant["id"])
    await flow_manager.initialize()
    await task.queue_frames([context_aggregator.user().get_context_frame()])
```

### Example Configuration

```python
flow_config = {
    "initial_node": "start",
    "nodes": {
        "start": {
            "role_messages": [
                {
                    "role": "system",
                    "content": "You are an order-taking assistant. You must ALWAYS use the available functions to progress the conversation. This is a phone conversation and your responses will be converted to audio. Keep the conversation friendly, casual, and polite. Avoid outputting special characters and emojis.",
                }
            ],
            "task_messages": [
                {
                    "role": "system",
                    "content": "You are an order-taking assistant. Ask if they want pizza or sushi."
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "choose_pizza",
                        "description": "User wants pizza",
                        "parameters": {"type": "object", "properties": {}},
                        "transition_to": "pizza_order"  # Specify transition
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "select_size",
                        "handler": select_size,
                        "description": "Select pizza size",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "size": {"type": "string", "enum": ["small", "medium", "large"]}
                            }
                        },
                        "transition_to": "toppings"  # Optional transition after processing
                    }
                }
            ]
        }
    }
}
```

### Transition Best Practices

- Use `transition_to` to make state changes explicit
- Combine handlers with transitions when appropriate
- Keep transitions focused on single responsibilities
- Use clear, descriptive names for target nodes
- Validate all transition targets exist
- Test both successful and failed transitions

## Dynamic Flows

Dynamic flows create and modify conversation paths at runtime based on data or business logic.

### Basic Setup

```python
from pipecat_flows import FlowManager

# Define transition callback
async def handle_transitions(function_name: str, args: Dict[str, Any], flow_manager):
    if function_name == "collect_age":
        if args["age"] < 25:
            await flow_manager.set_node("young_adult", create_young_adult_node())
        else:
            await flow_manager.set_node("standard", create_standard_node())

# Initialize flow manager with transition callback
flow_manager = FlowManager(
    task=task,
    llm=llm,
    tts=tts,
    transition_callback=handle_transitions
)

@transport.event_handler("on_first_participant_joined")
async def on_first_participant_joined(transport, participant):
    await transport.capture_participant_transcription(participant["id"])
    await flow_manager.initialize()
    await flow_manager.set_node("initial", create_initial_node())
    await task.queue_frames([context_aggregator.user().get_context_frame()])
```

### Node Creation

```python
from pipecat_flows import FlowArgs, FlowResult

async def calculate_quote(args: FlowArgs) -> FlowResult:
    """Calculate insurance quote."""
    coverage = args["coverage_amount"]
    monthly_premium = calculate_premium(coverage)
    return {
        "status": "success",
        "premium": monthly_premium
    }

def create_quote_node(customer_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a node for quote calculation."""
    return {
        "task_messages": [
            {
                "role": "system",
                "content": f"Calculate quote for {customer_data['age']} year old customer"
            }
        ],
        "functions": [
            {
                "type": "function",
                "function": {
                    "name": "calculate_quote",
                    "handler": calculate_quote,
                    "description": "Calculate insurance quote",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "coverage_amount": {"type": "integer"}
                        }
                    }
                }
            }
        ]
    }
```

### Best Practices

- Keep state in flow_manager.state
- Create separate functions for node creation
- Handle errors gracefully in transitions
- Document state dependencies
- Test node creation and transitions thoroughly