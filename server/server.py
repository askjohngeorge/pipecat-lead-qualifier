"""RTVI Bot Server Implementation.

This FastAPI server manages RTVI bot instances and provides endpoints for both
direct browser access and RTVI client connections. It handles:
- Creating Daily rooms
- Managing bot processes
- Providing connection credentials
- Monitoring bot status
"""

import argparse
import asyncio
import os
import subprocess
import sys
from contextlib import asynccontextmanager
from typing import Any, Dict, Literal

import aiohttp
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from loguru import logger

from pipecat.transports.services.helpers.daily_rest import (
    DailyRESTHelper,
    DailyRoomParams,
)
from bot_runner import configure
from unified_bot import main as unified_main

# Configure loguru - remove default handler and add our own
logger.remove()  # Remove default handler
logger.add(
    sys.stderr,
    level="DEBUG",
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    enqueue=True,  # Ensure thread-safe logging
    backtrace=True,  # Add exception context
    diagnose=True,  # Add variables to traceback
)

# Load environment variables from .env file
load_dotenv(override=True)

# Maximum number of bot instances allowed per room
MAX_BOTS_PER_ROOM = 1

# Dictionary to track bot processes: {pid: (process, room_url)}
bot_procs = {}

# Store Daily API helpers
daily_helpers = {}

# Global bot type configuration
BOT_TYPE: Literal["simple", "flow"] = "simple"


async def cleanup_finished_processes():
    while True:
        try:
            for pid in list(bot_procs.keys()):
                proc, room_url = bot_procs[pid]
                if proc.poll() is not None:
                    logger.info(
                        f"Cleaning up finished bot process {pid} for room {room_url}"
                    )
                    try:
                        await daily_helpers["rest"].delete_room_by_url(room_url)
                        logger.success(f"Successfully deleted room {room_url}")
                    except Exception as e:
                        logger.error(f"Failed to delete room {room_url}: {str(e)}")
                    del bot_procs[pid]
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
        await asyncio.sleep(5)


def cleanup():
    """Terminate all bot processes and cleanup resources."""
    for entry in bot_procs.values():
        proc, room_url = entry


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan manager that handles startup and shutdown tasks."""
    aiohttp_session = aiohttp.ClientSession()
    daily_helpers["rest"] = DailyRESTHelper(
        daily_api_key=os.getenv("DAILY_API_KEY", ""),
        daily_api_url=os.getenv("DAILY_API_URL", "https://api.daily.co/v1"),
        aiohttp_session=aiohttp_session,
    )

    # Start background cleanup task before yield
    cleanup_task = asyncio.create_task(cleanup_finished_processes())

    try:
        yield
    finally:
        # Cancel cleanup task
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass

        # Cleanup tasks
        await aiohttp_session.close()
        cleanup()


# Initialize FastAPI app with lifespan manager
app = FastAPI(lifespan=lifespan)

# Configure CORS to allow requests from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def create_room_and_token() -> tuple[str, str]:
    """Helper function to create a Daily room and generate an access token."""
    room = await daily_helpers["rest"].create_room(DailyRoomParams())
    if not room.url:
        raise HTTPException(status_code=500, detail="Failed to create room")

    token = await daily_helpers["rest"].get_token(room.url)
    if not token:
        raise HTTPException(
            status_code=500, detail=f"Failed to get token for room: {room.url}"
        )

    return room.url, token


@app.get("/")
async def start_agent(request: Request):
    """Endpoint for direct browser access to the bot."""
    logger.info(f"Creating room for {BOT_TYPE} bot")
    room_url, token = await create_room_and_token()
    logger.info(f"Room URL: {room_url}")

    # Check if there is already an existing process running in this room
    num_bots_in_room = sum(
        1
        for proc in bot_procs.values()
        if proc[1] == room_url and proc[0].poll() is None
    )
    if num_bots_in_room >= MAX_BOTS_PER_ROOM:
        raise HTTPException(
            status_code=500, detail=f"Max bot limit reached for room: {room_url}"
        )

    # Spawn a new bot process based on bot_type
    try:
        bot_module = "flow.bot" if BOT_TYPE == "flow" else "simple.simple_bot"
        proc = subprocess.Popen(
            [f"python3 -m {bot_module} -u {room_url} -t {token}"],
            shell=True,
            bufsize=1,
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
        bot_procs[proc.pid] = (proc, room_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start subprocess: {e}")

    return RedirectResponse(room_url)


@app.post("/connect")
async def rtvi_connect(request: Request) -> Dict[Any, Any]:
    """RTVI connect endpoint that creates a room and returns connection credentials."""
    logger.info(f"Creating room for RTVI connection with {BOT_TYPE} bot")
    room_url, token = await create_room_and_token()
    logger.info(f"Room URL: {room_url}")

    # Start the bot process
    try:
        bot_module = "flow.bot" if BOT_TYPE == "flow" else "simple.simple_bot"
        proc = subprocess.Popen(
            [f"python3 -m {bot_module} -u {room_url} -t {token}"],
            shell=True,
            bufsize=1,
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
        bot_procs[proc.pid] = (proc, room_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start subprocess: {e}")

    # Return the authentication bundle in format expected by DailyTransport
    return {"room_url": room_url, "token": token}


@app.get("/status/{pid}")
def get_status(pid: int):
    """Get the status of a specific bot process."""
    proc = bot_procs.get(pid)

    if not proc:
        raise HTTPException(
            status_code=404, detail=f"Bot with process id: {pid} not found"
        )

    status = "running" if proc[0].poll() is None else "finished"
    return JSONResponse({"bot_id": pid, "status": status})


async def main():
    """Run the appropriate bot type based on config."""
    parser = argparse.ArgumentParser(description="Bot Runner")
    parser.add_argument(
        "-t",
        "--type",
        type=str,
        choices=["simple", "flow"],
        default="simple",
        help="Type of bot to run",
    )
    args = parser.parse_args()

    # Get config file based on type
    config_file = f"config/{args.type}.json"

    # Create aiohttp session and Daily helper
    async with aiohttp.ClientSession() as session:
        daily_rest = DailyRESTHelper(
            daily_api_key=os.getenv("DAILY_API_KEY", ""),
            daily_api_url=os.getenv("DAILY_API_URL", "https://api.daily.co/v1"),
            aiohttp_session=session,
        )

        # Create room and get token
        room = await daily_rest.create_room(DailyRoomParams())
        if not room.url:
            raise Exception("Failed to create room")

        token = await daily_rest.get_token(room.url)
        if not token:
            raise Exception(f"Failed to get token for room: {room.url}")

        # Run unified bot with appropriate arguments
        await unified_main(
            ["--url", room.url, "--token", token, "--config", config_file]
        )


if __name__ == "__main__":
    asyncio.run(main())
