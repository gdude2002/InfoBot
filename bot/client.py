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

HELP_MESSAGES = [
    """
InfoBot is written and maintained by `gdude2002#5318`. If you've got a problem, please report it to the issue \
tracker at <https://github.com/gdude2002/InfoBot>.

__**About**__
InfoBot is designed for servers that have a semi-static information channel that provides essential information \
for users - for example, channels containing sets of rules, FAQs, useful links, channel lists, and general information.

The main problem with large channels of this type is adding information in the middle of the stack of messages - to do \
this manually, you have to delete all of the messages after that point, and repost them after you've added your \
new information.

InfoBot uses a section-based model to generate the content of the info channel for you. There are multiple types of \
section, and each may be configured individually for your needs.
    """,
    """
__**Commands**__
All commands (except for `help`) require the "Manage Server" permission.

• `config [<option> <value>]`: Set the value for a config option. Omit `option` and `value` to see the current config.
• `create <type> <section name>`: Create a new section - see below for supported types.
• `help`: This help message!
• `remove <section name>`: Remove a section 
• `section <command> || <section name> || <data>`: Run a section-specific command - see below for more details
• `setup [channel ID]`: Specify an info channel to manage - omit to create a default `#info` channel
• `update`: Reset the info channel and refill it with the latest changes

There are no information-listing commands - all of the data you need for these commands is listed in the info channel!
    """,
    """
__**Section types**__
The following section types are currently available.

• `faq` - A section holding sets of frequently-asked questions and answers. Section commands: `add`, `delete`, `set`.
• `text` - A free-form text section that can hold whatever you like. Section commands: `set`.

More section types are always being developed, and you may feel free to suggest new types and contribute your own \
here: <https://github.com/gdude2002/InfoBot>.
    """
]


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

    async def on_server_join(self, server):
        self.data_manager.add_server(server.id)
        # TODO: Initial setup and help message

    async def on_message(self, message):
        if message.server is None:
            return  # DM

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

        chars = self.data_manager.get_server_command_chars(message.server)
        if message.content.startswith(chars):  # It's a command
            text = message.content[len(chars):].strip()
            if " " in text:
                command, data = text.split(" ")
            else:
                command = text
                data = ""

            if hasattr(self, "command_{}".format(command)):
                await getattr(self, "command_{}".format(command))(data, message)

    # region Commands

    async def command_config(self, data, message):
        pass

    async def command_create(self, data, message):
        pass

    async def command_help(self, data, message):
        await self.send_message(message.channel, "{} \U0001F4EC".format(message.author.mention))
        for m in HELP_MESSAGES:
            await self.send_message(message.author, m)

    async def command_remove(self, data, message):
        pass

    async def command_section(self, data, message):
        try:
            section_name, command, data = data.split(" || ", 2)
        except Exception:
            return await self.send_message(
                message.channel,
                content="{} Command usage: `section <command> || <section name> || <data>`".format(message.author)
            )

        section = self.data_manager.get_section(message.server, section_name)

        if not section:
            return await self.send_message(message.channel, content="{} No such section: {}".format(
                message.author.mention, section_name
            ))

        try:
            result = section.process_command(command, data, self, message)
        except Exception:
            await self.send_message(message.channel, content="{} There was an error running that command. It's been "
                                                             "logged, but feel free to contact `gdude2002#5318` for "
                                                             "more info.".format(
                message.author.mention, section_name
            ))
            log.exception(
                "Error running section command `{}` for section `{}` on server `{}`".format(
                    command, section_name, message.server.id
                )
            )
        else:
            return await self.send_message(message.channel, content="{} {}".format(message.author.mention, result))

    async def command_setup(self, data, message):
        pass

    async def command_update(self, data, message):
        pass

# endregion

    pass
