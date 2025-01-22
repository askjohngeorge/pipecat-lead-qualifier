# Unified Bot Architecture Specification

## 1. Project Structure

```
unified_bot/
├── __init__.py
├── bot.py              # Main UnifiedBot class
├── config/
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── core.py     # Core config models (type, name, system_messages)
│   │   ├── flow.py     # Flow-specific models
│   │   └── pipeline.py # Pipeline configuration models
│   ├── loader.py       # Config loading and parsing
│   └── schemas/        
│       ├── core.json   # Basic bot configuration
│       ├── flow.json   # Flow-specific configuration
│       └── pipeline.json # Pipeline configuration
├── managers/
│   ├── __init__.py
│   ├── base.py        # Abstract base manager
│   ├── simple.py      # Simple context manager
│   └── flow.py        # Flow state manager
├── pipeline/
│   ├── __init__.py
│   └── builder.py     # Pipeline builder
└── utils/
    ├── __init__.py
    └── logging.py     # Logging configuration
```

## 2. Core Components

### 2.1 Configuration System

#### Core Configuration Schema (schemas/core.json)
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["type", "name", "system_messages"],
  "properties": {
    "type": {
      "type": "string",
      "enum": ["simple", "flow"]
    },
    "name": {
      "type": "string",
      "minLength": 1
    },
    "system_messages": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["role", "content"],
        "properties": {
          "role": {
            "type": "string",
            "enum": ["system", "assistant", "user"]
          },
          "content": {
            "type": "string"
          }
        }
      }
    }
  }
}
```

#### Flow Configuration Schema (schemas/flow.json)
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["initial_node", "nodes"],
  "properties": {
    "initial_node": {
      "type": "string"
    },
    "nodes": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "properties": {
          "role_messages": {
            "type": "array",
            "items": {
              "$ref": "#/definitions/message"
            }
          },
          "task_messages": {
            "type": "array",
            "items": {
              "$ref": "#/definitions/message"
            }
          },
          "functions": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "type": {
                  "type": "string"
                },
                "function": {
                  "type": "object"
                }
              }
            }
          }
        }
      }
    }
  }
}
```

#### Pipeline Configuration Schema (schemas/pipeline.json)
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "stt": {
      "type": "object",
      "properties": {
        "provider": {
          "type": "string",
          "enum": ["deepgram"]
        },
        "config": {
          "type": "object"
        }
      }
    },
    "tts": {
      "type": "object",
      "properties": {
        "provider": {
          "type": "string",
          "enum": ["deepgram"]
        },
        "voice": {
          "type": "string"
        }
      }
    },
    "llm": {
      "type": "object",
      "properties": {
        "provider": {
          "type": "string",
          "enum": ["openai"]
        },
        "model": {
          "type": "string"
        }
      }
    }
  }
}
```

### 2.2 Core Classes

#### Config Models (config/models/core.py)
```python
from pydantic import BaseModel
from typing import List, Optional

class Message(BaseModel):
    role: str
    content: str

class CoreConfig(BaseModel):
    type: str
    name: str
    system_messages: List[Message]
```

#### Flow Models (config/models/flow.py)
```python
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from .core import Message

class FlowNodeConfig(BaseModel):
    role_messages: Optional[List[Message]]
    task_messages: Optional[List[Message]]
    functions: Optional[List[Dict[str, Any]]]

class FlowConfig(BaseModel):
    initial_node: str
    nodes: Dict[str, FlowNodeConfig]
```

#### Pipeline Models (config/models/pipeline.py)
```python
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class PipelineConfig(BaseModel):
    stt: Dict[str, Any] = Field(default_factory=lambda: {"provider": "deepgram"})
    tts: Dict[str, Any] = Field(default_factory=lambda: {
        "provider": "deepgram",
        "voice": "aura-helios-en"
    })
    llm: Dict[str, Any] = Field(default_factory=lambda: {
        "provider": "openai",
        "model": "gpt-4"
    })
```

### 2.3 Manager Interface and Implementations

#### Base Manager (managers/base.py)
```python
from abc import ABC, abstractmethod
from typing import Any
from pipecat.pipeline.task import PipelineTask
from ..config.models.core import CoreConfig

class BaseManager(ABC):
    def __init__(self, config: CoreConfig, pipeline_task: PipelineTask):
        self.config = config
        self.pipeline_task = pipeline_task
        
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the manager."""
        pass
        
    @abstractmethod
    async def handle_message(self, message: str) -> Any:
        """Handle incoming message."""
        pass
        
    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup resources."""
        pass
```

#### Simple Manager (managers/simple.py)
```python
from .base import BaseManager
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext

class SimpleManager(BaseManager):
    async def initialize(self):
        self.context = OpenAILLMContext(self.config.system_messages)
        await self.pipeline_task.queue_frames([self.context.get_context_frame()])
        
    async def handle_message(self, message: str):
        response = await self.pipeline_task.process_message(message)
        return response
        
    async def cleanup(self):
        pass
```

#### Flow Manager (managers/flow.py)
```python
from typing import Dict, Any, Optional
from .base import BaseManager
from ..config.models.flow import FlowConfig
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext

class FlowManager(BaseManager):
    def __init__(self, config: CoreConfig, pipeline_task: PipelineTask, flow_config: FlowConfig):
        super().__init__(config, pipeline_task)
        self.flow_config = flow_config
        self.current_node = None
        self.flow_data: Dict[str, Any] = {}
        
    async def initialize(self):
        self.current_node = self.flow_config.initial_node
        node_config = self.flow_config.nodes[self.current_node]
        
        self.context = OpenAILLMContext(node_config.role_messages)
        await self.pipeline_task.queue_frames([self.context.get_context_frame()])
        
    async def handle_message(self, message: str):
        node_config = self.flow_config.nodes[self.current_node]
        
        response = await self.pipeline_task.process_message(message)
        
        if node_config.functions:
            next_node = await self.handle_functions(response, node_config.functions)
            if next_node:
                await self.transition_to(next_node)
                
        return response
        
    async def transition_to(self, node_name: str):
        if node_name not in self.flow_config.nodes:
            raise ValueError(f"Invalid node name: {node_name}")
            
        self.current_node = node_name
        node_config = self.flow_config.nodes[node_name]
        
        if node_config.role_messages:
            self.context = OpenAILLMContext(node_config.role_messages)
            await self.pipeline_task.queue_frames([self.context.get_context_frame()])
        
    async def handle_functions(self, response: Dict, functions: list) -> Optional[str]:
        if "function_call" not in response:
            return None
            
        function_name = response["function_call"]["name"]
        for func in functions:
            if func["function"]["name"] == function_name:
                if "transition_to" in func["function"]:
                    return func["function"]["transition_to"]
        return None
        
    async def cleanup(self):
        self.flow_data.clear()
```

### 2.4 Pipeline Builder

```python
from typing import List
from pipecat.pipeline.pipeline import Pipeline
from pipecat.services.deepgram import DeepgramSTTService, DeepgramTTSService
from pipecat.services.openai import OpenAILLMService
from ..config.models.pipeline import PipelineConfig

class PipelineBuilder:
    def __init__(self, pipeline_config: PipelineConfig):
        self.config = pipeline_config
        self.components: List = []
        self.transport = None
        self.llm = None
        
    def add_transport(self, transport):
        self.transport = transport
        self.components.append(transport.input())
        return self
        
    def add_stt(self):
        stt_config = self.config.stt
        if stt_config["provider"] == "deepgram":
            stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"))
            self.components.append(stt)
        return self
        
    def add_llm(self):
        llm_config = self.config.llm
        if llm_config["provider"] == "openai":
            self.llm = OpenAILLMService(
                api_key=os.getenv("OPENAI_API_KEY"),
                model=llm_config["model"]
            )
            self.components.append(self.llm)
        return self
        
    def build(self) -> Pipeline:
        if not self.transport:
            raise ValueError("Transport must be configured before building pipeline")
            
        self.components.append(self.transport.output())
        return Pipeline(self.components)
```

### 2.5 UnifiedBot Implementation

```python
from typing import Optional
from pipecat.pipeline.task import PipelineParams, PipelineTask
from .config.loader import load_config
from .pipeline.builder import PipelineBuilder
from .managers.simple import SimpleManager
from .managers.flow import FlowManager

class UnifiedBot:
    def __init__(self, config_path: str):
        self.config = load_config(config_path)
        self.pipeline = None
        self.pipeline_task = None
        self.manager = None
        
    async def initialize(self, transport):
        # Build pipeline (if pipeline config exists)
        if hasattr(self.config, 'pipeline'):
            builder = PipelineBuilder(self.config.pipeline)
        else:
            # Use default pipeline configuration
            builder = PipelineBuilder(PipelineConfig())
            
        builder.add_transport(transport)
        builder.add_stt()
        builder.add_llm()
        
        self.pipeline = builder.build()
        
        # Create pipeline task
        self.pipeline_task = PipelineTask(
            self.pipeline,
            PipelineParams(
                allow_interruptions=True,
                enable_metrics=True,
                enable_usage_metrics=True
            )
        )
        
        # Create appropriate manager
        if self.config.type == "simple":
            self.manager = SimpleManager(self.config, self.pipeline_task)
        else:
            self.manager = FlowManager(
                self.config, 
                self.pipeline_task,
                self.config.flow_config
            )
            
        await self.manager.initialize()
        
    async def run(self):
        if not self.manager:
            raise RuntimeError("Bot must be initialized before running")
        
        await self.manager.run()
```

## 3. Component Interactions

The system follows these key interaction patterns:

1. Configuration Loading:
   - Core configuration is always required (type, name, system_messages)
   - Flow configuration is loaded for flow-type bots
   - Pipeline configuration is optional, defaults provided

2. Pipeline Construction:
   - Pipeline can be built with default or custom configuration
   - Components are added in a specific order
   - All pipelines share the same basic structure

3. Manager Lifecycle:
   - Managers handle bot-specific logic
   - SimpleManager for stateless conversations
   - FlowManager for state-based interactions
   - Both use the same underlying pipeline

4. Runtime Flow:
   - Transport handles audio I/O
   - STT converts audio to text
   - LLM processes text with context
   - TTS converts responses to audio
   - Manager orchestrates the process

This architecture supports incremental implementation while maintaining a clear separation of concerns between configuration, pipeline management, and conversation handling.
