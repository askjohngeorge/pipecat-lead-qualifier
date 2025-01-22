# Revised Staged Migration Plan

## Stage 1: System Message Configuration
**Goal**: Move system prompts to external configuration

1. Create basic config structure:
```json
{
  "type": "simple",
  "name": "Simple Voice Assistant",
  "system_messages": [
    {
      "role": "system",
      "content": "..."
    }
  ]
}
```

2. Add simple config loading:
```python
# config/models.py
class Message(BaseModel):
    role: str
    content: str

class BotConfig(BaseModel):
    type: str
    name: str
    system_messages: List[Message]
```

3. Modify simple_bot.py to load messages from config:
```python
async def main():
    config = load_config("configs/simple.json")
    messages = config.system_messages
    context = OpenAILLMContext(messages)
```

**Test Point**: Run simple_bot.py with externally configured prompts

## Stage 2: Flow Configuration Support 
**Goal**: Support flow configurations while keeping pipeline setup the same

1. Extend config for flow:
```json
{
  "type": "flow",
  "name": "Lead Qualification Bot",
  "flow_config": {
    "initial_node": "rapport_building",
    "nodes": {
      "rapport_building": {
        "role_messages": [
          {
            "role": "system",
            "content": "..."
          }
        ],
        "task_messages": [
          {
            "role": "system",
            "content": "..."
          }
        ],
        "functions": [...]
      }
    }
  }
}
```

2. Update config models:
```python
class FlowNodeConfig(BaseModel):
    role_messages: Optional[List[Message]]
    task_messages: Optional[List[Message]]
    functions: Optional[List[Dict]]

class FlowConfig(BaseModel):
    initial_node: str
    nodes: Dict[str, FlowNodeConfig]

class BotConfig(BaseModel):
    type: str
    name: str
    system_messages: Optional[List[Message]]
    flow_config: Optional[FlowConfig]
```

3. Modify bot.py to handle both configs while keeping pipeline setup the same

**Test Point**: Both bots should work with their respective configs

## Stage 3: Unified Bot Structure
**Goal**: Create unified structure while still using hardcoded pipeline

1. Create BaseManager abstract class
2. Implement SimpleManager and FlowManager
3. Create UnifiedBot class that uses appropriate manager
4. Update server.py to use UnifiedBot

**Test Point**: Server should handle both types using config files

## Stage 4: Pipeline Configuration
**Goal**: Make pipeline components configurable

1. Add pipeline config:
```json
{
  "pipeline": {
    "stt": {
      "provider": "deepgram"
    },
    "tts": {
      "provider": "deepgram",
      "voice": "aura-helios-en"
    },
    "llm": {
      "provider": "openai",
      "model": "gpt-4"
    }
  }
}
```

2. Create PipelineBuilder
3. Move pipeline setup from bot code to builder
4. Update UnifiedBot to use PipelineBuilder

**Test Point**: Should work same as before but with configurable pipeline

## Stage 5: Polish and Error Handling
**Goal**: Production-ready implementation

1. Add proper error handling for config loading
2. Add validation for pipeline configurations
3. Add logging throughout
4. Clean up any temporary code

**Test Point**: System should handle errors gracefully

Each stage builds on the previous one while maintaining working functionality. The order ensures we handle the most important configuration needs first (system prompts) before moving on to more complex structural changes.