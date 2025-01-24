Below is a **step-by-step refactoring plan** for your junior developer. The aim is to move all the **common setup logic** (transport creation, pipeline building, event registration, etc.) from the specialized bot classes (`SimpleBot`, `FlowBot`) into the **base** or supporting utils while **keeping** the domain-specific logic (system prompts, flow definitions, helper functions) where it is for now.

---

## **1. Identify Repeated Boilerplate in `SimpleBot` and `FlowBot`**

Take a close look at what’s in both `SimpleBot` and `FlowBot`:

- **Setup**:
  - `await bot.setup_services()`
  - `await bot.setup_transport(args.url, args.token)`
  - `bot.create_pipeline()`
  - `await bot.start()`

- **Command-line argument parsing** in the `main()` function.
- **Transport creation** logic in `_create_transport`.
- **Pipeline building** steps in `_create_pipeline_impl` (though `FlowBot` adds the flow manager, and `SimpleBot` is more straightforward).
- **Common event handlers**, like finishing up on participant left.

Look for code that’s largely identical or can be abstracted into shared functions.

---

## **2. Move Common Setup to the `BaseBot` or Utility Methods**

Focus on removing as much code duplication from `SimpleBot` and `FlowBot` as possible, while leaving their domain-specific details:

1. **Create a “run_bot” helper** in the base or in a utility file:
   ```python
   # e.g. in bot_framework.py
   import argparse
   import asyncio
   from aiohttp import ClientSession

   async def run_bot(bot_class, config_class):
       parser = argparse.ArgumentParser(...)
       parser.add_argument("-u", "--url", ...)
       parser.add_argument("-t", "--token", ...)
       args = parser.parse_args()

       config = config_class()  # e.g. AppConfig
       bot = bot_class(config)

       async with ClientSession() as session:
           await bot.setup_services()
           await bot.setup_transport(args.url, args.token)
           bot.create_pipeline()
           await bot.start()
   ```
   - Then in `simple/bot.py`, you’d do:
     ```python
     from utils.bot_framework import run_bot

     async def main():
         await run_bot(SimpleBot, AppConfig)

     if __name__ == "__main__":
         import asyncio
         asyncio.run(main())
     ```
   - Same in `flow/bot.py`, reducing code duplication in your `main()` function.

2. **Transport Creation & Pipeline**  
   - Your `BaseBot.setup_transport(...)` is already fairly generic. If you see repeated patterns—like “capture transcription” or “stop pipeline on participant left”—they can remain in the base or be placed in `_setup_transport_impl()`.  
   - Similarly, your `create_pipeline()` method in the base can handle the “rtvi → stt → llm → tts → transport output” chain. If there’s something unique in `FlowBot`, you can override `_create_pipeline_impl()` but keep it minimal.

3. **Event Handling**  
   - If both bots do the same “stop when participant leaves,” put that in `BaseBot` by default. If a bot has a special handler (FlowBot might do extra stuff on participant left), override `_setup_transport_impl()` and add it there.

---

## **3. (Optional) Introduce Specialized Base Classes**

If you notice you’re adding a bunch of “if flow vs. if simple” logic in `BaseBot`, you can split it out:

- **`SinglePromptBaseBot`**: Inherits from `BaseBot`. It might handle straightforward “one system prompt, no flows.”  
- **`FlowBaseBot`**: Inherits from `BaseBot`. It might handle “flow manager” logic.  

But if you want to keep it simpler, you can keep a single `BaseBot` for now and just let `FlowBot` override the `_create_pipeline_impl()` method.

---

## **4. Keep Domain-Specific Logic in Each Bot**

For now, do **not** relocate:

- **System prompts** or “flow config” dictionaries (like `handle_availability_check` or `handle_time_slot_selection`)—these remain in their respective bot modules or config files.  
- **Flow-specific functions** remain with the flow bot.  
- **Simple-bot tasks** remain with the simple bot.

In other words, you only extract the “common scaffolding.” The actual logic to parse or handle that data is specialized.

---

## **5. Verify Everything Still Works**

After each step, test:

- Running `python -m simple.bot -u ... -t ...`
- Running `python -m flow.bot -u ... -t ...`

Make sure the calls to the new “shared” methods in `BaseBot` or your new “run_bot” function still produce the same result in each environment. 

---

## **Example of the Final Look (High-Level)**

After implementing the changes above, your `simple.bot` might look like:

```python
# simple/bot.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from utils.config import AppConfig
from utils.bot_framework import BaseBot, run_bot
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from .config_simple import SIMPLE_BOT_CONFIG

class SimpleBot(BaseBot):
    def __init__(self, config: AppConfig):
        super().__init__(config)
        self.bot_config = SIMPLE_BOT_CONFIG
        self.messages = [
            {"role": "system", "content": self.bot_config["system_prompt"]}
        ]

    async def _setup_services_impl(self):
        self.context = OpenAILLMContext(self.messages)
        self.context_aggregator = self.services.llm.create_context_aggregator(self.context)

    async def _create_transport(self, factory, url: str, token: str):
        return factory.create_simple_assistant_transport(url, token)

    async def _handle_first_participant(self):
        self.messages.append({"role": "system", "content": "Please introduce yourself..."})
        await self.task.queue_frames([self.context_aggregator.user().get_context_frame()])

async def main():
    await run_bot(SimpleBot, AppConfig)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

And your `BaseBot` might now hold all the logic for event registration, pipeline building, etc. Meanwhile, `FlowBot` is similarly minimal, just focusing on flow-specific tasks.

---

## **Checklist for the Junior Developer**

1. **Extract repeated code** from `SimpleBot` and `FlowBot` into `BaseBot` (or further utility methods).  
2. **Optionally** add a `run_bot` utility function to unify the argument parsing and main loop.  
3. **Ensure** that only the domain-specific logic (system prompts, flow definitions, specialized event handling) remains in `SimpleBot`/`FlowBot`.  
4. **Test** each stage to confirm the refactoring hasn’t introduced regressions.  

Following these steps will leave you with a cleaner structure, where each specialized bot only deals with the *unique*, domain-specific aspects—while the shared “scaffolding” (setup/transport/pipeline/event handling) lives in the base or utility files.