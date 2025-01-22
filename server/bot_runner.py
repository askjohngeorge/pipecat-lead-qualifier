#
# Copyright (c) 2024, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

import argparse
import os

import aiohttp
from pipecat.transports.services.daily import DailyRESTHelper


async def configure(aiohttp_session: aiohttp.ClientSession):
    """Configure and return Daily room URL and token."""
    url = os.getenv("DAILY_SAMPLE_ROOM_URL")
    key = os.getenv("DAILY_API_KEY")

    if not url or not key:
        raise Exception("Missing Daily configuration")

    daily_rest_helper = DailyRESTHelper(
        daily_api_key=key,
        daily_api_url="https://api.daily.co/v1",
        aiohttp_session=aiohttp_session,
    )

    # Create token with 1-hour expiry
    token = await daily_rest_helper.get_token(url, 60 * 60)
    return (url, token)


async def configure_with_args(
    aiohttp_session: aiohttp.ClientSession,
    parser: argparse.ArgumentParser | None = None,
):
    if not parser:
        parser = argparse.ArgumentParser(description="Daily AI SDK Bot Sample")
    parser.add_argument(
        "-u", "--url", type=str, required=False, help="URL of the Daily room to join"
    )
    parser.add_argument(
        "-k",
        "--apikey",
        type=str,
        required=False,
        help="Daily API Key (needed to create an owner token for the room)",
    )

    args, unknown = parser.parse_known_args()

    url = args.url or os.getenv("DAILY_SAMPLE_ROOM_URL")
    key = args.apikey or os.getenv("DAILY_API_KEY")

    if not url:
        raise Exception(
            "No Daily room specified. use the -u/--url option from the command line, or set DAILY_SAMPLE_ROOM_URL in your environment to specify a Daily room URL."
        )

    if not key:
        raise Exception(
            "No Daily API key specified. use the -k/--apikey option from the command line, or set DAILY_API_KEY in your environment to specify a Daily API key, available from https://dashboard.daily.co/developers."
        )

    daily_rest_helper = DailyRESTHelper(
        daily_api_key=key,
        daily_api_url=os.getenv("DAILY_API_URL", "https://api.daily.co/v1"),
        aiohttp_session=aiohttp_session,
    )

    # Create a meeting token for the given room with an expiration 1 hour in
    # the future.
    expiry_time: float = 60 * 60

    token = await daily_rest_helper.get_token(url, expiry_time)

    return (url, token, args)
