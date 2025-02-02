# ./pipecat_flows/actions.py
```python
#
# Copyright (c) 2024, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

"""Action management system for conversation flows.

This module provides the ActionManager class which handles execution of actions
during conversation state transitions. It supports:
- Built-in actions (TTS, conversation ending)
- Custom action registration
- Synchronous and asynchronous handlers
- Pre and post-transition actions
- Error handling and validation

Actions are used to perform side effects during conversations, such as:
- Text-to-speech output
- Database updates
- External API calls
- Custom integrations
"""

import asyncio
from typing import Any, Callable, Dict, List, Optional

from loguru import logger
from pipecat.frames.frames import (
    EndFrame,
    TTSSpeakFrame,
)
from pipecat.pipeline.task import PipelineTask

from .exceptions import ActionError
from .types import ActionConfig


class ActionManager:
    """Manages the registration and execution of flow actions.

    Actions are executed during state transitions and can include:
    - Text-to-speech output
    - Database updates
    - External API calls
    - Custom user-defined actions

    Built-in actions:
    - tts_say: Speak text using TTS
    - end_conversation: End the current conversation

    Custom actions can be registered using register_action().
    """

    def __init__(self, task: PipelineTask, tts=None):
        """Initialize the action manager.

        Args:
            task: PipelineTask instance used to queue frames
            tts: Optional TTS service for voice actions
        """
        self.action_handlers: Dict[str, Callable] = {}
        self.task = task
        self.tts = tts

        # Register built-in actions
        self._register_action("tts_say", self._handle_tts_action)
        self._register_action("end_conversation", self._handle_end_action)

    def _register_action(self, action_type: str, handler: Callable) -> None:
        """Register a handler for a specific action type.

        Args:
            action_type: String identifier for the action (e.g., "tts_say")
            handler: Async or sync function that handles the action

        Raises:
            ValueError: If handler is not callable
        """
        if not callable(handler):
            raise ValueError("Action handler must be callable")
        self.action_handlers[action_type] = handler
        logger.debug(f"Registered handler for action type: {action_type}")

    async def execute_actions(self, actions: Optional[List[ActionConfig]]) -> None:
        """Execute a list of actions.

        Args:
            actions: List of action configurations to execute

        Raises:
            ActionError: If action execution fails

        Note:
            Each action must have a 'type' field matching a registered handler
        """
        if not actions:
            return

        for action in actions:
            action_type = action.get("type")
            if not action_type:
                raise ActionError("Action missing required 'type' field")

            handler = self.action_handlers.get(action_type)
            if not handler:
                raise ActionError(f"No handler registered for action type: {action_type}")

            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(action)
                else:
                    handler(action)
                logger.debug(f"Successfully executed action: {action_type}")
            except Exception as e:
                raise ActionError(f"Failed to execute action {action_type}: {str(e)}") from e

    async def _handle_tts_action(self, action: dict) -> None:
        """Built-in handler for TTS actions.

        Args:
            action: Action configuration containing 'text' to speak
        """
        if not self.tts:
            logger.warning("TTS action called but no TTS service provided")
            return

        text = action.get("text")
        if not text:
            logger.error("TTS action missing 'text' field")
            return

        try:
            await self.tts.say(text)
            # TODO: Update to TTSSpeakFrame once Pipecat is fixed
            # await self.task.queue_frame(TTSSpeakFrame(text=action["text"]))
        except Exception as e:
            logger.error(f"TTS error: {e}")

    async def _handle_end_action(self, action: dict) -> None:
        """Built-in handler for ending the conversation.

        This handler queues an EndFrame to terminate the conversation. If the action
        includes a 'text' key, it will queue that text to be spoken before ending.

        Args:
            action: Dictionary containing the action configuration.
                Optional 'text' key for a goodbye message.
        """
        if action.get("text"):  # Optional goodbye message
            await self.task.queue_frame(TTSSpeakFrame(text=action["text"]))
        await self.task.queue_frame(EndFrame())
```

# ./pipecat_flows/__init__.py
```python
#
# Copyright (c) 2024, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#
"""
Pipecat Flows.

This package provides a framework for building structured conversations in Pipecat.
The FlowManager can handle both static and dynamic conversation flows:

1. Static Flows:
   - Configuration-driven conversations with predefined paths
   - Entire flow structure defined upfront
   - Example:
        from pipecat_flows import FlowArgs, FlowResult

        async def collect_name(args: FlowArgs) -> FlowResult:
            name = args["name"]
            return {"status": "success", "name": name}

        flow_config = {
            "initial_node": "greeting",
            "nodes": {
                "greeting": {
                    "messages": [...],
                    "functions": [{
                        "type": "function",
                        "function": {
                            "name": "collect_name",
                            "handler": collect_name,
                            "description": "...",
                            "parameters": {...},
                            "transition_to": "next_step"
                        }
                    }]
                }
            }
        }
        flow_manager = FlowManager(task, llm, flow_config=flow_config)

2. Dynamic Flows:
   - Runtime-determined conversations
   - Nodes created or modified during execution
   - Example:
        from pipecat_flows import FlowArgs, FlowResult

        async def collect_age(args: FlowArgs) -> FlowResult:
            age = args["age"]
            return {"status": "success", "age": age}

        async def handle_transitions(function_name: str, args: Dict, flow_manager):
            if function_name == "collect_age":
                await flow_manager.set_node("next_step", create_next_node())

        flow_manager = FlowManager(task, llm, transition_callback=handle_transitions)
"""

from .exceptions import (
    ActionError,
    FlowError,
    FlowInitializationError,
    FlowTransitionError,
    InvalidFunctionError,
)
from .manager import FlowManager
from .types import FlowArgs, FlowConfig, FlowResult, NodeConfig

__all__ = [
    # Flow Manager
    "FlowManager",
    # Types
    "FlowArgs",
    "FlowConfig",
    "FlowResult",
    "NodeConfig",
    # Exceptions
    "FlowError",
    "FlowInitializationError",
    "FlowTransitionError",
    "InvalidFunctionError",
    "ActionError",
]
```

# ./pipecat_flows/types.py
```python
#
# Copyright (c) 2024, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

"""Type definitions for the conversation flow system.

This module defines the core types used throughout the flow system:
- FlowResult: Function return type
- FlowArgs: Function argument type
- NodeConfig: Node configuration type
- FlowConfig: Complete flow configuration type

These types provide structure and validation for flow configurations
and function interactions.
"""

from typing import Any, Awaitable, Callable, Dict, List, TypedDict, TypeVar

T = TypeVar("T")
TransitionHandler = Callable[[Dict[str, T], "FlowManager"], Awaitable[None]]
"""Type for transition handler functions.

Args:
    args: Dictionary of arguments from the function call
    flow_manager: Reference to the FlowManager instance

Returns:
    None: Handlers are expected to update state and set next node
"""


class FlowResult(TypedDict, total=False):
    """Base type for function results.

    Example:
        {
            "status": "success",
            "data": {"processed": True},
            "error": None  # Optional error message
        }
    """

    status: str
    error: str


FlowArgs = Dict[str, Any]
"""Type alias for function handler arguments.

Example:
    {
        "user_name": "John",
        "age": 25,
        "preferences": {"color": "blue"}
    }
"""


class ActionConfigRequired(TypedDict):
    """Required fields for action configuration."""

    type: str


class ActionConfig(ActionConfigRequired, total=False):
    """Configuration for an action.

    Required:
        type: Action type identifier (e.g. "tts_say", "notify_slack")

    Optional:
        handler: Callable to handle the action
        text: Text for tts_say action
        Additional fields are allowed and passed to the handler
    """

    handler: Callable[[Dict[str, Any]], Awaitable[None]]
    text: str


class NodeConfigRequired(TypedDict):
    """Required fields for node configuration."""

    task_messages: List[dict]
    functions: List[dict]


class NodeConfig(NodeConfigRequired, total=False):
    """Configuration for a single node in the flow.

    Required fields:
        task_messages: List of message dicts defining the current node's objectives
        functions: List of function definitions in provider-specific format

    Optional fields:
        role_messages: List of message dicts defining the bot's role/personality
        pre_actions: Actions to execute before LLM inference
        post_actions: Actions to execute after LLM inference

    Example:
        {
            "role_messages": [
                {
                    "role": "system",
                    "content": "You are a helpful assistant..."
                }
            ],
            "task_messages": [
                {
                    "role": "system",
                    "content": "Ask the user for their name..."
                }
            ],
            "functions": [...],
            "pre_actions": [...],
            "post_actions": [...]
        }
    """

    role_messages: List[Dict[str, Any]]
    pre_actions: List[ActionConfig]
    post_actions: List[ActionConfig]


class FlowConfig(TypedDict):
    """Configuration for the entire conversation flow.

    Attributes:
        initial_node: Name of the starting node
        nodes: Dictionary mapping node names to their configurations

    Example:
        {
            "initial_node": "greeting",
            "nodes": {
                "greeting": {
                    "role_messages": [...],
                    "task_messages": [...],
                    "functions": [...],
                    "pre_actions": [...]
                },
                "process_order": {
                    "task_messages": [...],
                    "functions": [...],
                    "post_actions": [...]
                }
            }
        }
    """

    initial_node: str
    nodes: Dict[str, NodeConfig]
```

# ./pipecat_flows/exceptions.py
```python
#
# Copyright (c) 2024, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

"""Custom exceptions for the conversation flow system.

This module defines the exception hierarchy used throughout the flow system:
- FlowError: Base exception for all flow-related errors
- FlowInitializationError: Initialization failures
- FlowTransitionError: State transition issues
- InvalidFunctionError: Function registration/calling problems
- ActionError: Action execution failures

These exceptions provide specific error types for better error handling
and debugging.
"""


class FlowError(Exception):
    """Base exception for all flow-related errors."""

    pass


class FlowInitializationError(FlowError):
    """Raised when flow initialization fails."""

    pass


class FlowTransitionError(FlowError):
    """Raised when a state transition fails."""

    pass


class InvalidFunctionError(FlowError):
    """Raised when an invalid or unavailable function is called."""

    pass


class ActionError(FlowError):
    """Raised when an action execution fails."""

    pass
```

# ./pipecat_flows/manager.py
```python
#
# Copyright (c) 2024, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

"""Core conversation flow management system.

This module provides the FlowManager class which orchestrates conversations
across different LLM providers. It supports:
- Static flows with predefined paths
- Dynamic flows with runtime-determined transitions
- State management and transitions
- Function registration and execution
- Action handling
- Cross-provider compatibility

The flow manager coordinates all aspects of a conversation, including:
- LLM context management
- Function registration
- State transitions
- Action execution
- Error handling
"""

import copy
import inspect
import sys
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict, List, Optional, Set, Union

from loguru import logger
from pipecat.frames.frames import (
    FunctionCallResultProperties,
    LLMMessagesAppendFrame,
    LLMMessagesUpdateFrame,
    LLMSetToolsFrame,
)
from pipecat.pipeline.task import PipelineTask

from .actions import ActionError, ActionManager
from .adapters import create_adapter
from .exceptions import FlowError, FlowInitializationError, FlowTransitionError
from .types import ActionConfig, FlowArgs, FlowConfig, FlowResult, NodeConfig, TransitionHandler

if TYPE_CHECKING:
    from pipecat.services.anthropic import AnthropicLLMService
    from pipecat.services.google import GoogleLLMService
    from pipecat.services.openai import OpenAILLMService

    LLMService = Union[OpenAILLMService, AnthropicLLMService, GoogleLLMService]
else:
    LLMService = Any


class FlowManager:
    """Manages conversation flows, supporting both static and dynamic configurations.

    The FlowManager orchestrates conversation flows by managing state transitions,
    function registration, and message handling across different LLM providers.

    Attributes:
        task: Pipeline task for frame queueing
        llm: LLM service instance (OpenAI, Anthropic, or Google)
        tts: Optional TTS service for voice actions
        state: Shared state dictionary across nodes
        current_node: Currently active node identifier
        initialized: Whether the manager has been initialized
        nodes: Node configurations for static flows
        current_functions: Currently registered function names
    """

    def __init__(
        self,
        *,
        task: PipelineTask,
        llm: LLMService,
        context_aggregator: Any,
        tts: Optional[Any] = None,
        flow_config: Optional[FlowConfig] = None,
    ):
        """Initialize the flow manager.

        Args:
            task: PipelineTask instance for queueing frames
            llm: LLM service instance (e.g., OpenAI, Anthropic)
            context_aggregator: Context aggregator for updating user context
            tts: Optional TTS service for voice actions
            flow_config: Optional static flow configuration. If provided,
                operates in static mode with predefined nodes

        Raises:
            ValueError: If any transition handler is not a valid async callable
        """
        self.task = task
        self.llm = llm
        self.tts = tts
        self.action_manager = ActionManager(task, tts)
        self.adapter = create_adapter(llm)
        self.initialized = False
        self._context_aggregator = context_aggregator
        self._pending_function_calls = 0

        # Set up static or dynamic mode
        if flow_config:
            self.nodes = flow_config["nodes"]
            self.initial_node = flow_config["initial_node"]
            logger.debug("Initialized in static mode")
        else:
            self.nodes = {}
            self.initial_node = None
            logger.debug("Initialized in dynamic mode")

        self.state: Dict[str, Any] = {}  # Shared state across nodes
        self.current_functions: Set[str] = set()  # Track registered functions
        self.current_node: Optional[str] = None

    def _validate_transition_callback(self, name: str, callback: Any) -> None:
        """Validate a transition callback.

        Args:
            name: Name of the function the callback is for
            callback: The callback to validate

        Raises:
            ValueError: If callback is not a valid async callable
        """
        if not callable(callback):
            raise ValueError(f"Transition callback for {name} must be callable")
        if not inspect.iscoroutinefunction(callback):
            raise ValueError(f"Transition callback for {name} must be async")

    async def initialize(self) -> None:
        """Initialize the flow manager."""
        if self.initialized:
            logger.warning(f"{self.__class__.__name__} already initialized")
            return

        try:
            self.initialized = True
            logger.debug(f"Initialized {self.__class__.__name__}")

            # If in static mode, set initial node
            if self.initial_node:
                logger.debug(f"Setting initial node: {self.initial_node}")
                await self.set_node(self.initial_node, self.nodes[self.initial_node])

        except Exception as e:
            self.initialized = False
            raise FlowInitializationError(f"Failed to initialize flow: {str(e)}") from e

    def register_action(self, action_type: str, handler: Callable) -> None:
        """Register a handler for a specific action type.

        Args:
            action_type: String identifier for the action (e.g., "tts_say")
            handler: Async or sync function that handles the action

        Example:
            async def custom_notification(action: dict):
                text = action.get("text", "")
                await notify_user(text)

            flow_manager.register_action("notify", custom_notification)
        """
        self.action_manager._register_action(action_type, handler)

    def _register_action_from_config(self, action: ActionConfig) -> None:
        """Register an action handler from action configuration.

        Args:
            action: Action configuration dictionary containing type and optional handler

        Raises:
            ActionError: If action type is not registered and no valid handler provided
        """
        action_type = action.get("type")
        handler = action.get("handler")

        # Register action if not already registered
        if action_type and action_type not in self.action_manager.action_handlers:
            # Register handler if provided
            if handler and callable(handler):
                self.register_action(action_type, handler)
                logger.debug(f"Registered action handler from config: {action_type}")
            # Raise error if no handler provided and not a built-in action
            elif action_type not in ["tts_say", "end_conversation"]:
                raise ActionError(
                    f"Action '{action_type}' not registered. "
                    "Provide handler in action config or register manually."
                )

    async def _call_handler(self, handler: Callable, args: FlowArgs) -> FlowResult:
        """Call handler with or without args based on its signature.

        Args:
            handler: The function to call
            args: Arguments dictionary

        Returns:
            Dict[str, Any]: Handler result
        """
        sig = inspect.signature(handler)
        if "args" in sig.parameters:
            return await handler(args)
        return await handler()

    async def _handle_static_transition(
        self,
        function_name: str,
        args: Dict[str, Any],
        flow_manager: "FlowManager",
    ) -> None:
        """Handle transitions for static flows.

        Transitions to a new node in static flows by looking up the node
        configuration and setting it as the current node. Logs a warning
        if the target node is not found in the flow configuration.

        Args:
            function_name: Name of the target node to transition to
            args: Arguments passed to the function that triggered the transition
            flow_manager: Reference to the FlowManager instance
        """
        if function_name in self.nodes:
            logger.debug(f"Static transition to node: {function_name}")
            await self.set_node(function_name, self.nodes[function_name])
        else:
            logger.warning(f"Static transition failed: Node '{function_name}' not found")

    async def _create_transition_func(
        self,
        name: str,
        handler: Optional[Callable],
        transition_to: Optional[str],
        transition_callback: Optional[Callable] = None,
    ) -> Callable:
        """Create a transition function for the given name and handler.

        Args:
            name: Name of the function being registered
            handler: Optional function to process data
            transition_to: Optional node to transition to (static flows)
            transition_callback: Optional callback for dynamic transitions

        Returns:
            Callable: Async function that handles the tool invocation

        Raises:
            ValueError: If both transition_to and transition_callback are specified
        """
        if transition_to and transition_callback:
            raise ValueError(
                f"Function {name} cannot have both transition_to and transition_callback"
            )

        # Validate transition callback if provided
        if transition_callback:
            self._validate_transition_callback(name, transition_callback)

        is_edge_function = bool(transition_to) or bool(transition_callback)

        def decrease_pending_function_calls() -> None:
            """Decrease the pending function calls counter if greater than zero."""
            if self._pending_function_calls > 0:
                self._pending_function_calls -= 1
                logger.debug(
                    f"Function call completed: {name} (remaining: {self._pending_function_calls})"
                )

        async def on_context_updated_edge(args: Dict[str, Any], result_callback: Callable) -> None:
            """Handle context updates for edge functions with transitions."""
            try:
                decrease_pending_function_calls()

                # Only process transition if this was the last pending call
                if self._pending_function_calls == 0:
                    if transition_to:  # Static flow
                        logger.debug(f"Static transition to: {transition_to}")
                        await self.set_node(transition_to, self.nodes[transition_to])
                    elif transition_callback:  # Dynamic flow
                        logger.debug(f"Dynamic transition for: {name}")
                        await transition_callback(args, self)
                    # Reset counter after transition completes
                    self._pending_function_calls = 0
                    logger.debug("Reset pending function calls counter")
                else:
                    logger.debug(
                        f"Skipping transition, {self._pending_function_calls} calls still pending"
                    )
            except Exception as e:
                logger.error(f"Error in transition: {str(e)}")
                self._pending_function_calls = 0
                await result_callback(
                    {"status": "error", "error": str(e)},
                    properties=None,  # Clear properties to prevent further callbacks
                )
                raise  # Re-raise to prevent further processing

        async def on_context_updated_node() -> None:
            """Handle context updates for node functions without transitions."""
            decrease_pending_function_calls()

        async def transition_func(
            function_name: str,
            tool_call_id: str,
            args: Dict[str, Any],
            llm: Any,
            context: Any,
            result_callback: Callable,
        ) -> None:
            """Inner function that handles the actual tool invocation."""
            try:
                # Track pending function call
                self._pending_function_calls += 1
                logger.debug(
                    f"Function call pending: {name} (total: {self._pending_function_calls})"
                )

                # Execute handler if present
                if handler:
                    result = await self._call_handler(handler, args)
                    logger.debug(f"Handler completed for {name}")
                else:
                    result = {"status": "acknowledged"}
                    logger.debug(f"Function called without handler: {name}")

                # For edge functions, prevent LLM completion until transition (run_llm=False)
                # For node functions, allow immediate completion (run_llm=True)
                async def on_context_updated() -> None:
                    if is_edge_function:
                        await on_context_updated_edge(args, result_callback)
                    else:
                        await on_context_updated_node()

                properties = FunctionCallResultProperties(
                    run_llm=not is_edge_function,
                    on_context_updated=on_context_updated,
                )
                await result_callback(result, properties=properties)

            except Exception as e:
                logger.error(f"Error in transition function {name}: {str(e)}")
                self._pending_function_calls = 0
                error_result = {"status": "error", "error": str(e)}
                await result_callback(error_result)

        return transition_func

    def _lookup_function(self, func_name: str) -> Callable:
        """Look up a function by name in the main module.

        Args:
            func_name: Name of the function to look up

        Returns:
            Callable: The found function

        Raises:
            FlowError: If function is not found
        """
        main_module = sys.modules["__main__"]
        handler = getattr(main_module, func_name, None)

        if handler is not None:
            logger.debug(f"Found function '{func_name}' in main module")
            return handler

        error_message = (
            f"Function '{func_name}' not found in main module.\n"
            "Ensure the function is defined in your main script "
            "or imported into it."
        )

        raise FlowError(error_message)

    async def _register_function(
        self,
        name: str,
        new_functions: Set[str],
        handler: Optional[Callable],
        transition_to: Optional[str] = None,
        transition_callback: Optional[Callable] = None,
    ) -> None:
        """Register a function with the LLM if not already registered.

        Args:
            name: Name of the function to register with the LLM
            handler: Either a callable function or a string. If string starts with
                    '__function__:', extracts the function name after the prefix
            transition_to: Optional node name to transition to after function execution
            transition_callback: Optional callback for dynamic transitions
            new_functions: Set to track newly registered functions for this node

        Raises:
            FlowError: If function registration fails or handler lookup fails
        """
        if name not in self.current_functions:
            try:
                # Handle special token format (e.g. "__function__:function_name")
                if isinstance(handler, str) and handler.startswith("__function__:"):
                    func_name = handler.split(":")[1]
                    handler = self._lookup_function(func_name)

                self.llm.register_function(
                    name,
                    await self._create_transition_func(
                        name, handler, transition_to, transition_callback
                    ),
                )
                new_functions.add(name)
                logger.debug(f"Registered function: {name}")
            except Exception as e:
                logger.error(f"Failed to register function {name}: {str(e)}")
                raise FlowError(f"Function registration failed: {str(e)}") from e

    def _remove_handlers(self, tool_config: Dict[str, Any]) -> None:
        """Remove handlers from tool configuration.

        Args:
            tool_config: Function configuration to clean
        """
        if "function" in tool_config and "handler" in tool_config["function"]:
            del tool_config["function"]["handler"]
        elif "handler" in tool_config:
            del tool_config["handler"]
        elif "function_declarations" in tool_config:
            for decl in tool_config["function_declarations"]:
                if "handler" in decl:
                    del decl["handler"]

    def _remove_transition_info(self, tool_config: Dict[str, Any]) -> None:
        """Remove transition information from tool configuration.

        Removes transition_to and transition_callback fields to prevent them from being
        sent to the LLM provider.

        Args:
            tool_config: Function configuration to clean
        """
        if "function" in tool_config:
            # Clean OpenAI format
            if "transition_to" in tool_config["function"]:
                del tool_config["function"]["transition_to"]
            if "transition_callback" in tool_config["function"]:
                del tool_config["function"]["transition_callback"]
        elif "function_declarations" in tool_config:
            # Clean Gemini format
            for decl in tool_config["function_declarations"]:
                if "transition_to" in decl:
                    del decl["transition_to"]
                if "transition_callback" in decl:
                    del decl["transition_callback"]
        else:
            # Clean Anthropic format
            if "transition_to" in tool_config:
                del tool_config["transition_to"]
            if "transition_callback" in tool_config:
                del tool_config["transition_callback"]

    async def set_node(self, node_id: str, node_config: NodeConfig) -> None:
        """Set up a new conversation node and transition to it.

        Handles the complete node transition process in the following order:
        1. Execute pre-actions (if any)
        2. Set up messages (role and task)
        3. Register node functions
        4. Update LLM context with messages and tools
        5. Update state (current node and functions)
        6. Trigger LLM completion with new context
        7. Execute post-actions (if any)

        Args:
            node_id: Identifier for the new node
            node_config: Complete configuration for the node

        Raises:
            FlowTransitionError: If manager not initialized
            FlowError: If node setup fails
        """
        if not self.initialized:
            raise FlowTransitionError(f"{self.__class__.__name__} must be initialized first")

        try:
            self._validate_node_config(node_id, node_config)
            logger.debug(f"Setting node: {node_id}")

            # Register action handlers from config
            for action_list in [
                node_config.get("pre_actions", []),
                node_config.get("post_actions", []),
            ]:
                for action in action_list:
                    self._register_action_from_config(action)

            # Execute pre-actions if any
            if pre_actions := node_config.get("pre_actions"):
                await self._execute_actions(pre_actions=pre_actions)

            # Combine role and task messages
            messages = []
            if role_messages := node_config.get("role_messages"):
                messages.extend(role_messages)
            messages.extend(node_config["task_messages"])

            # Register functions and prepare tools
            tools = []
            new_functions: Set[str] = set()

            for func_config in node_config["functions"]:
                # Handle Gemini's nested function declarations
                if "function_declarations" in func_config:
                    for declaration in func_config["function_declarations"]:
                        name = declaration["name"]
                        handler = declaration.get("handler")
                        transition_to = declaration.get("transition_to")
                        transition_callback = declaration.get("transition_callback")
                        logger.debug(f"Processing function: {name}")
                        await self._register_function(
                            name=name,
                            new_functions=new_functions,
                            handler=handler,
                            transition_to=transition_to,
                            transition_callback=transition_callback,
                        )
                else:
                    name = self.adapter.get_function_name(func_config)
                    logger.debug(f"Processing function: {name}")

                    # Extract handler and transition info based on format
                    if "function" in func_config:
                        handler = func_config["function"].get("handler")
                        transition_to = func_config["function"].get("transition_to")
                        transition_callback = func_config["function"].get("transition_callback")
                    else:
                        handler = func_config.get("handler")
                        transition_to = func_config.get("transition_to")
                        transition_callback = func_config.get("transition_callback")

                    await self._register_function(
                        name=name,
                        new_functions=new_functions,
                        handler=handler,
                        transition_to=transition_to,
                        transition_callback=transition_callback,
                    )

                # Create tool config (after removing handler and transition info)
                tool_config = copy.deepcopy(func_config)
                self._remove_handlers(tool_config)
                self._remove_transition_info(tool_config)
                tools.append(tool_config)

            # Let adapter format tools for provider
            formatted_tools = self.adapter.format_functions(tools)

            # Update LLM context
            await self._update_llm_context(messages, formatted_tools)
            logger.debug("Updated LLM context")

            # Update state
            self.current_node = node_id
            self.current_functions = new_functions

            # Trigger completion with new context
            if self._context_aggregator:
                await self.task.queue_frames([self._context_aggregator.user().get_context_frame()])

            # Execute post-actions if any
            if post_actions := node_config.get("post_actions"):
                await self._execute_actions(post_actions=post_actions)

            logger.debug(f"Successfully set node: {node_id}")

        except Exception as e:
            logger.error(f"Error setting node {node_id}: {str(e)}")
            raise FlowError(f"Failed to set node {node_id}: {str(e)}") from e

    async def _update_llm_context(self, messages: List[dict], functions: List[dict]) -> None:
        """Update LLM context with new messages and functions.

        Args:
            messages: New messages to add to context
            functions: New functions to make available

        Raises:
            FlowError: If context update fails
        """
        try:
            # Determine frame type based on whether this is the first node
            frame_type = (
                LLMMessagesUpdateFrame if self.current_node is None else LLMMessagesAppendFrame
            )

            await self.task.queue_frames(
                [frame_type(messages=messages), LLMSetToolsFrame(tools=functions)]
            )

            logger.debug(f"Updated LLM context using {frame_type.__name__}")
        except Exception as e:
            logger.error(f"Failed to update LLM context: {str(e)}")
            raise FlowError(f"Context update failed: {str(e)}") from e

    async def _execute_actions(
        self,
        pre_actions: Optional[List[ActionConfig]] = None,
        post_actions: Optional[List[ActionConfig]] = None,
    ) -> None:
        """Execute pre and post actions.

        Args:
            pre_actions: Actions to execute before context update
            post_actions: Actions to execute after context update
        """
        if pre_actions:
            await self.action_manager.execute_actions(pre_actions)
        if post_actions:
            await self.action_manager.execute_actions(post_actions)

    def _validate_node_config(self, node_id: str, config: NodeConfig) -> None:
        """Validate the configuration of a conversation node.

        This method ensures that:
        1. Required fields (task_messages, functions) are present
        2. Functions have valid configurations based on their type:
        - Node functions must have either a handler or transition_to
        - Edge functions (matching node names) are allowed without handlers
        3. Function configurations match the LLM provider's format

        Args:
            node_id: Identifier for the node being validated
            config: Complete node configuration to validate

        Raises:
            ValueError: If configuration is invalid or missing required fields
        """
        # Check required fields
        if "task_messages" not in config:
            raise ValueError(f"Node '{node_id}' missing required 'task_messages' field")
        if "functions" not in config:
            raise ValueError(f"Node '{node_id}' missing required 'functions' field")

        # Validate each function configuration
        for func in config["functions"]:
            try:
                name = self.adapter.get_function_name(func)
            except KeyError:
                raise ValueError(f"Function in node '{node_id}' missing name field")

            # Skip validation for edge functions (matching node names)
            if name in self.nodes:
                continue

            # Check for handler in provider-specific formats
            has_handler = (
                ("function" in func and "handler" in func["function"])  # OpenAI format
                or "handler" in func  # Anthropic format
                or (  # Gemini format
                    "function_declarations" in func
                    and func["function_declarations"]
                    and "handler" in func["function_declarations"][0]
                )
            )

            # Check for transition_to in provider-specific formats
            has_transition_to = (
                ("function" in func and "transition_to" in func["function"])
                or "transition_to" in func
                or (
                    "function_declarations" in func
                    and func["function_declarations"]
                    and "transition_to" in func["function_declarations"][0]
                )
            )

            # Check for transition_callback in provider-specific formats
            has_transition_callback = (
                ("function" in func and "transition_callback" in func["function"])
                or "transition_callback" in func
                or (
                    "function_declarations" in func
                    and func["function_declarations"]
                    and "transition_callback" in func["function_declarations"][0]
                )
            )

            # Warn if function has no handler or transitions
            if not has_handler and not has_transition_to and not has_transition_callback:
                logger.warning(
                    f"Function '{name}' in node '{node_id}' has neither handler, transition_to, nor transition_callback"
                )
```

# ./pipecat_flows/adapters.py
```python
#
# Copyright (c) 2024, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

"""LLM provider adapters for normalizing function and message formats.

This module provides adapters that normalize interactions between different
LLM providers (OpenAI, Anthropic, Gemini). It handles:
- Function name extraction
- Argument parsing
- Message content formatting
- Provider-specific schema conversion

The adapter system allows the flow manager to work with different LLM
providers while maintaining a consistent internal format (based on OpenAI's
function calling convention).
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from loguru import logger


class LLMAdapter(ABC):
    """Base adapter for LLM-specific format handling.

    Adapters normalize differences between LLM providers:
    - OpenAI: Uses function calling format
    - Anthropic: Uses native function format
    - Google: Uses function declarations format

    This allows the flow system to work consistently across
    different LLM providers while handling format differences
    internally.
    """

    @abstractmethod
    def get_function_name(self, function_def: Dict[str, Any]) -> str:
        """Extract function name from provider-specific function definition."""
        pass

    @abstractmethod
    def get_function_args(self, function_call: Dict[str, Any]) -> dict:
        """Extract function arguments from provider-specific function call."""
        pass

    @abstractmethod
    def get_message_content(self, message: Dict[str, Any]) -> str:
        """Extract message content from provider-specific format."""
        pass

    @abstractmethod
    def format_functions(self, functions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format functions for provider-specific use."""
        pass


class OpenAIAdapter(LLMAdapter):
    """Format adapter for OpenAI.

    Handles OpenAI's function calling format, which is used as the default format
    in the flow system.
    """

    def get_function_name(self, function_def: Dict[str, Any]) -> str:
        """Extract function name from OpenAI function definition.

        Args:
            function_def: OpenAI-formatted function definition dictionary

        Returns:
            Function name from the definition
        """
        return function_def["function"]["name"]

    def get_function_args(self, function_call: Dict[str, Any]) -> dict:
        """Extract arguments from OpenAI function call.

        Args:
            function_call: OpenAI-formatted function call dictionary

        Returns:
            Dictionary of function arguments, empty if none provided
        """
        return function_call.get("arguments", {})

    def get_message_content(self, message: Dict[str, Any]) -> str:
        """Extract content from OpenAI message format.

        Args:
            message: OpenAI-formatted message dictionary

        Returns:
            Message content as string
        """
        return message["content"]

    def format_functions(self, functions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format functions for OpenAI use.

        Args:
            functions: List of function definitions

        Returns:
            Functions in OpenAI format (unchanged as this is our default format)
        """
        return functions


class AnthropicAdapter(LLMAdapter):
    """Format adapter for Anthropic.

    Handles Anthropic's native function format, converting between OpenAI's format
    and Anthropic's as needed.
    """

    def get_function_name(self, function_def: Dict[str, Any]) -> str:
        """Extract function name from Anthropic function definition.

        Args:
            function_def: Anthropic-formatted function definition dictionary

        Returns:
            Function name from the definition
        """
        return function_def["name"]

    def get_function_args(self, function_call: Dict[str, Any]) -> dict:
        """Extract arguments from Anthropic function call.

        Args:
            function_call: Anthropic-formatted function call dictionary

        Returns:
            Dictionary of function arguments, empty if none provided
        """
        return function_call.get("arguments", {})

    def get_message_content(self, message: Dict[str, Any]) -> str:
        """Extract content from Anthropic message format.

        Handles both string content and structured content arrays.

        Args:
            message: Anthropic-formatted message dictionary

        Returns:
            Message content as string, concatenated if from multiple parts
        """
        if isinstance(message.get("content"), list):
            return " ".join(item["text"] for item in message["content"] if item["type"] == "text")
        return message.get("content", "")

    def format_functions(self, functions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format functions for Anthropic use.

        Converts from OpenAI format to Anthropic's native function format if needed.

        Args:
            functions: List of function definitions in OpenAI format

        Returns:
            Functions converted to Anthropic's format
        """
        formatted = []
        for func in functions:
            if "function" in func:
                # Convert from OpenAI format
                formatted.append(
                    {
                        "name": func["function"]["name"],
                        "description": func["function"].get("description", ""),
                        "input_schema": func["function"].get("parameters", {}),
                    }
                )
            else:
                # Already in Anthropic format
                formatted.append(func)
        return formatted


class GeminiAdapter(LLMAdapter):
    """Format adapter for Google's Gemini.

    Handles Gemini's function declarations format, converting between OpenAI's format
    and Gemini's as needed.
    """

    def get_function_name(self, function_def: Dict[str, Any]) -> str:
        """Extract function name from Gemini function definition.

        Args:
            function_def: Gemini-formatted function definition dictionary

        Returns:
            Function name from the first declaration, or empty string if none found
        """
        logger.debug(f"Getting function name from: {function_def}")
        if "function_declarations" in function_def:
            declarations = function_def["function_declarations"]
            if declarations and isinstance(declarations, list):
                return declarations[0]["name"]
        return ""

    def get_function_args(self, function_call: Dict[str, Any]) -> dict:
        """Extract arguments from Gemini function call.

        Args:
            function_call: Gemini-formatted function call dictionary

        Returns:
            Dictionary of function arguments, empty if none provided
        """
        return function_call.get("args", {})

    def get_message_content(self, message: Dict[str, Any]) -> str:
        """Extract content from Gemini message format.

        Args:
            message: Gemini-formatted message dictionary

        Returns:
            Message content as string
        """
        return message["content"]

    def format_functions(self, functions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format functions for Gemini use.

        Converts from OpenAI format to Gemini's function declarations format.

        Args:
            functions: List of function definitions in OpenAI format

        Returns:
            Functions converted to Gemini's format with declarations wrapper
        """
        all_declarations = []
        for func in functions:
            if "function_declarations" in func:
                # Process each declaration separately
                for decl in func["function_declarations"]:
                    formatted_decl = {
                        "name": decl["name"],
                        "description": decl.get("description", ""),
                        "parameters": decl.get("parameters", {"type": "object", "properties": {}}),
                    }
                    all_declarations.append(formatted_decl)
            elif "function" in func:
                all_declarations.append(
                    {
                        "name": func["function"]["name"],
                        "description": func["function"].get("description", ""),
                        "parameters": func["function"].get("parameters", {}),
                    }
                )
        return [{"function_declarations": all_declarations}] if all_declarations else []


def create_adapter(llm) -> LLMAdapter:
    """Create appropriate adapter based on LLM service type.

    Uses lazy imports to avoid requiring all provider dependencies at runtime.
    Only the dependency for the chosen provider needs to be installed.

    Args:
        llm: LLM service instance

    Returns:
        LLMAdapter: Provider-specific adapter

    Raises:
        ValueError: If LLM type is not supported or required dependency not installed
    """
    # Try OpenAI
    try:
        from pipecat.services.openai import OpenAILLMService

        if isinstance(llm, OpenAILLMService):
            logger.debug("Creating OpenAI adapter")
            return OpenAIAdapter()
    except ImportError as e:
        logger.debug(f"OpenAI import failed: {e}")

    # Try Anthropic
    try:
        from pipecat.services.anthropic import AnthropicLLMService

        if isinstance(llm, AnthropicLLMService):
            logger.debug("Creating Anthropic adapter")
            return AnthropicAdapter()
    except ImportError as e:
        logger.debug(f"Anthropic import failed: {e}")

    # Try Google
    try:
        from pipecat.services.google import GoogleLLMService

        if isinstance(llm, GoogleLLMService):
            logger.debug("Creating Google adapter")
            return GeminiAdapter()
    except ImportError as e:
        logger.debug(f"Google import failed: {e}")

    # If we get here, either the LLM type is not supported or the required dependency is not installed
    llm_type = type(llm).__name__
    error_msg = f"Unsupported LLM type or missing dependency: {llm_type}\n"
    error_msg += "Make sure you have installed the required dependency:\n"
    error_msg += "- For OpenAI: pip install 'pipecat-ai[openai]'\n"
    error_msg += "- For Anthropic: pip install 'pipecat-ai[anthropic]'\n"
    error_msg += "- For Google: pip install 'pipecat-ai[google]'"

    raise ValueError(error_msg)
```

