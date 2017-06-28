# coding=utf-8
import aiohttp
import asyncio
import discord
import logging
from ruamel.yaml import yaml

import json
import os

from aiohttp import ServerDisconnectedError
from discord import Object, Embed, Colour, Member
from discord import Status


log = logging.getLogger("bot")

__author__ = 'Gareth Coles'


class Client(discord.client.Client):
    def __init__(self, *, loop=None, **options):
        super().__init__(loop=loop, **options)

        self.banned_ids = []
        self.config = yaml.load(open("config.yml", "r"))

    def get_token(self):
        return self.config["token"]

    async def on_message(self, message):
        if message.server is None:
            return
        else:
            logger = logging.getLogger(message.server.name)

        if message.author.id == self.user.id:
            pass

        user = "{}#{}".format(
            message.author.name, message.author.discriminator
        )

        for line in message.content.split("\n"):
            logger.debug("#{} / {} {}".format(
                message.channel.name,
                user, line
            ))
