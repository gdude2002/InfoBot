# coding=utf-8
import datetime

import aiohttp
import asyncio
import discord
import logging
from ruamel import yaml

import json
import os

import traceback
from aiohttp import ServerDisconnectedError
from discord import Object, Embed, Colour, Member
from discord import Status

from bot.data import DataManager

log = logging.getLogger("bot")

__author__ = 'Gareth Coles'

LOG_COLOURS = {
    logging.INFO: Colour.blue(),
    logging.WARNING: Colour.gold(),
    logging.ERROR: Colour.red(),
    logging.CRITICAL: Colour.dark_red()
}


class Client(discord.client.Client):
    def __init__(self, *, loop=None, **options):
        super().__init__(loop=loop, **options)

        self.banned_ids = []
        self.config = yaml.safe_load(open("config.yml", "r"))
        self.data_manager = DataManager()

    def get_token(self):
        return self.config["token"]

    def log_to_channel(self, record: logging.LogRecord):
        if not self.config.get("log_channel"):
            return

        channel = self.get_channel(self.config["log_channel"])

        if not channel:
            return

        dt = datetime.datetime.fromtimestamp(
            record.created
        )

        description = record.msg

        if record.exc_info:
            description += "\n\n```{}```".format("\n".join(traceback.format_exception(*record.exc_info)))

        embed = Embed(
            title="{} / {}".format(record.name, record.levelname),
            description=description
        )

        if record.levelno in LOG_COLOURS:
            embed.colour = LOG_COLOURS[record.levelno]

        embed.set_footer(text=dt.strftime("%B %d %Y, %H:%M:%S"))

        async def inner():
            await self.send_message(channel, embed=embed)

        self.loop.call_soon_threadsafe(asyncio.async, inner())

    def sections_updated(self, server):
        pass

    async def on_ready(self):
        log.info("Setting up...")
        self.data_manager.load()

        for server in self.servers:
            self.data_manager.add_server(server.id)

        log.info("Ready!")

    async def on_message(self, message):
        if message.server is None:
            return

        if message.author.id == self.user.id:
            return

        logger = logging.getLogger(message.server.name)

        user = "{}#{}".format(
            message.author.name, message.author.discriminator
        )

        for line in message.content.split("\n"):
            logger.debug("#{} / {} {}".format(
                message.channel.name,
                user, line
            ))
