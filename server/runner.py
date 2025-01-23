#
# Copyright (c) 2024, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

import argparse
import os

import aiohttp
from pipecat.transports.services.helpers.daily_rest import DailyRESTHelper
from utils.config import AppConfig


async def configure(aiohttp_session: aiohttp.ClientSession):
    """Configure and return Daily room URL and token."""
    # This is only used when no URL/token is provided via command line
    raise Exception(
        "Daily room URL and token must be provided via command line arguments"
    )


async def configure_with_args(
    aiohttp_session: aiohttp.ClientSession,
    parser: argparse.ArgumentParser | None = None,
):
    if not parser:
        parser = argparse.ArgumentParser(description="Daily AI SDK Bot Sample")
    parser.add_argument(
        "-u", "--url", type=str, required=True, help="URL of the Daily room to join"
    )
    parser.add_argument(
        "-t", "--token", type=str, required=True, help="Token for the Daily room"
    )

    args, unknown = parser.parse_known_args()

    if not args.url or not args.token:
        raise Exception(
            "Daily room URL and token must be provided via command line arguments"
        )

    return (args.url, args.token, args)
