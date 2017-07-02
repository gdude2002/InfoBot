# coding=utf-8
import datetime
import logging
import re
import shlex
import traceback

import asyncio
import discord

from aiohttp import ServerDisconnectedError, ClientSession
from discord import Embed, Colour
from ruamel import yaml

from bot.data import DataManager

log = logging.getLogger("bot")

__author__ = 'Gareth Coles'

GIST_URL = "https://api.github.com/gists/{}"
GIST_REGEX = re.compile(r"gist:[a-z0-9]+")

LOG_COLOURS = {
    logging.INFO: Colour.blue(),
    logging.WARNING: Colour.gold(),
    logging.ERROR: Colour.red(),
    logging.CRITICAL: Colour.dark_red()
}

CONFIG_KEY_DESCRIPTIONS = {
    "control_chars": "Characters that all commands must be prefixed with. You can always mention me as well instead.",
    "info_channel": "ID for the currently-configured info channel. Use the `setup` command if you want to change this."
}

WELCOME_MESSAGE = [
    """
Hello! I was invited to this server to manage an info-channel.

Please use `!setup <channel ID>` to specify which channel to manage, or `!help` for more information on how I work.

Note: Management commands require the **Manage Server** permission. Issues can be reported to \
<https://github.com/gdude2002/InfoBot>.
    """
]

HELP_MESSAGE = """
InfoBot is written and maintained by `gdude2002#5318`. If you've got a problem, please report it to the issue \
tracker at <https://github.com/gdude2002/InfoBot>.

To read up on how to use me, you should really take a look at our documentation on the wiki. You can find that here: \
<https://github.com/gdude2002/InfoBot/wiki>
"""


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

    async def close(self):
        log.info("Shutting down...")
        self.data_manager.save()
        await discord.client.Client.close(self)

    def sections_updated(self, server):
        self.data_manager.save_server(server.id)

    async def on_ready(self):
        log.info("Setting up...")
        self.data_manager.load()

        for server in self.servers:
            self.data_manager.add_server(server.id)

        log.info("Ready!")

    async def on_server_join(self, server):
        self.data_manager.add_server(server.id)

        for message in WELCOME_MESSAGE:
            await self.send_message(server.default_channel, content=message)

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
        text = None

        if message.content.startswith(chars):  # It's a command
            text = message.content[len(chars):].strip()
        elif message.content.startswith(self.user.mention):
            text = message.content[len(self.user.mention):].strip()

        if text:
            if " " in text:
                command, args = text.split(" ", 1)
            else:
                command = text
                args = ""

            args_string = args
            args = shlex.split(args)

            if len(args) > 0:
                data = args[0:]

                if GIST_REGEX.match(data[-1]):
                    gist_id = data.pop(-1).split(":")[1]
                    gist_url = GIST_URL.format(gist_id)

                    log.debug("Grabbing gist info: {}".format(gist_id))

                    session = ClientSession()

                    async with session.get(gist_url) as response:
                        gist_json = await response.json()

                    session.close()

                    if "files" not in gist_json:
                        return await self.send_message(
                            message.channel, "{} No such gist: `{}`".format(message.author.mention, gist_id)
                        )

                    for filename, file in gist_json["files"].items():
                        log.debug("Gist file collected: {}".format(filename))
                        data.append(file["content"])
            else:
                data = []

            log.debug("Command: {}".format(repr(command)))
            log.debug("Args: {}".format(repr(args)))
            log.debug("Args string: {}".format(repr(args_string)))
            log.debug("Data: {}".format(repr(data)))

            if hasattr(self, "command_{}".format(command)):
                await getattr(self, "command_{}".format(command))(data, args_string, message)

    async def clear_channel(self, channel):
        current_index = None
        last_index = None
        num_errors = 0

        while current_index != -1:
            if num_errors >= 5:
                break

            try:
                async for message in self.logs_from(channel, before=current_index):
                    current_index = message
                    await self.delete_message(message)
            except ServerDisconnectedError:
                try:
                    async for message in self.logs_from(channel, before=current_index):
                        current_index = message
                        await self.delete_message(message)
                except Exception:
                    num_errors += 1
                    continue
            except Exception:
                num_errors += 1
                continue

            if last_index == current_index:
                break

            last_index = current_index

    # region Commands

    async def command_config(self, data, data_string, message):
        if not message.author.server_permissions.manage_server:
            return log.debug("Permission denied")  # No perms

        if len(data) < 1:
            config = self.data_manager.get_config(message.server)

            md = "__**Current configuration**__\n\n"

            for key, value in config.items():
                md += "**{}**: `{}`\n".format(key, value)

            await self.send_message(
                message.channel, "{}\n\n{}".format(message.author.mention, md)
            )

        elif len(data) < 2:
            config = self.data_manager.get_config(message.server)
            key = data[0].lower()

            if key not in config:
                return await self.send_message(
                    message.channel, "{} Unknown key: `{}`".format(message.author.mention, key)
                )

            await self.send_message(
                message.channel, "{} **{}** is set to `{}`\n\n**Info**: {}".format(
                    message.author.mention, key, config[key], CONFIG_KEY_DESCRIPTIONS[key]
                )
            )
        else:
            config = self.data_manager.get_config(message.server)
            key, value = data[0].lower(), data[1]

            if key == "info_channel":
                return await self.send_message(
                    message.channel, "{} Please use the `setup` command to change the info channel instead.".format(
                        message.author.mention
                    )
                )

            if key not in config:
                return await self.send_message(
                    message.channel, "{} Unknown key: `{}`".format(message.author.mention, key)
                )

            self.data_manager.set_config(message.server, key, value)
            self.data_manager.save_server(message.server.id)

            await self.send_message(
                message.channel, "{} **{}** is now set to `{}`".format(
                    message.author.mention, key, value
                )
            )

    async def command_create(self, data, data_string, message):
        if not message.author.server_permissions.manage_server:
            return log.debug("Permission denied")  # No perms

        if len(data) < 2:
            return await self.send_message(
                message.channel, "{} Usage: `create <section type> \"<section name>\"`".format(message.author.mention)
            )

        section_type, section_name = data[0], data[1]

        if self.data_manager.get_section(message.server, section_name):
            return await self.send_message(
                message.channel, "{} A section named `{}` already exists".format(
                    message.author.mention, section_name
                )
            )

        clazz = self.data_manager.get_section_class(section_type)

        if not clazz:
            return await self.send_message(
                message.channel, "{} Unknown section type: `{}`".format(
                    message.author.mention, section_type
                )
            )

        section = clazz(section_name)
        self.data_manager.add_section(message.server, section)
        self.data_manager.save_server(message.server.id)

        await self.send_message(
            message.channel,
            "{} Section created: `{}`\n\nRun the `update` command to wipe the info channel and add it.".format(
                message.author.mention, section_name
            )
        )

    async def command_help(self, data, data_string, message):
        await self.send_message(message.channel, "{}\n\n{}".format(message.author.mention, HELP_MESSAGE))

    async def command_remove(self, data, data_string, message):
        if not message.author.server_permissions.manage_server:
            return log.debug("Permission denied")  # No perms

        if len(data) < 1:
            return await self.send_message(
                message.channel, "{} Usage: `remove \"<section name>\"`".format(message.author.mention)
            )

        section_name = data[0]

        if not self.data_manager.get_section(message.server, section_name):
            return await self.send_message(
                message.channel, "{} No such section: `{}`\n\nPerhaps you meant to surround the section name with "
                                 "\"quotes\"?".format(message.author.mention, section_name)
            )

        self.data_manager.remove_section(message.server, section_name)
        self.data_manager.save_server(message.server.id)

        await self.send_message(
            message.channel,
            "{} Section removed: `{}`\n\nRun the `update` command to wipe the info channel and recreate without "
            "it.".format(
                message.author.mention, section_name
            )
        )

    async def command_section(self, data, data_string, message):
        if not message.author.server_permissions.manage_server:
            return log.debug("Permission denied")  # No perms

        try:
            section_name, command = data[0], data[1]

            if len(data) > 2:
                data = data[2:]
            else:
                data = []
        except Exception:
            return await self.send_message(
                message.channel,
                content="{} Command usage: `section \"<section name>\" <command> [data ...]`".format(
                    message.author.mention
                )
            )

        section = self.data_manager.get_section(message.server, section_name)

        if not section:
            return await self.send_message(message.channel, content="{} No such section: {}".format(
                message.author.mention, section_name
            ))

        try:
            result = section.process_command(command, data, data_string, self, message)
        except Exception:
            await self.send_message(
                message.channel,
                content="{} There was an error running that command. It's been logged, but feel free "
                        "to raise an issue.".format(message.author.mention, section_name)
            )
            log.exception(
                "Error running section command `{}` for section `{}` on server `{}`".format(
                    command, section_name, message.server.id
                )
            )
        else:
            return await self.send_message(message.channel, content="{} {}".format(message.author.mention, result))

    async def command_setup(self, data, data_string, message):
        if not message.author.server_permissions.manage_server:
            return log.debug("Permission denied")  # No perms

        if len(data) > 1:
            return await self.send_message(
                message.channel,
                content="{} Usage: `setup <channel ID>`".format(message.author.mention)
            )

        try:
            channel = self.get_channel(str(int(data[0])))
        except Exception:
            return await self.send_message(
                message.channel,
                content="{} Command usage: `setup <channel ID>`".format(message.author.mention)
            )

        if channel not in message.server.channels:
            return await self.send_message(
                message.channel,
                content="{} Unable to find channel for ID `{}`".format(message.author.mention, data[0])
            )

        self.data_manager.set_channel(message.server, channel)

        await self.send_message(
            message.channel,
            content="{} Info channel set to {}\n\nRun the `update` command to wipe and fill it. Note that you cannot "
                    "undo this operation - **all messages in the info channel will be removed**!\n\n**__*MAKE SURE "
                    "YOU SELECTED THE CORRECT CHANNEL!*__**".format(message.author.mention, channel.mention)
        )

    async def command_update(self, data, data_string, message):
        if not message.author.server_permissions.manage_server:
            return log.debug("Permission denied")  # No perms

        channel = self.data_manager.get_channel(message.server)

        if not channel:
            return await self.send_message(
                message.channel,
                "{} No info channel has been set for this server. Try the `setup` command!".format(
                    message.author.mention
                )
            )

        channel = self.get_channel(channel)

        if not channel:
            return await self.send_message(
                message.channel,
                "{} The configured info channel no longer exists. Set another with the `setup` command!".format(
                    message.author.mention
                )
            )

        await self.clear_channel(channel)

        sections = self.data_manager.get_sections(message.server)

        for name, section in sections:
            await self.send_message(channel, "**__{}__**".format(name))

            for part in section.render():
                await self.send_message(channel, "\n{}".format(part))

        await self.send_message(
            message.channel,
            "{} The info channel has been updated!".format(
                message.author.mention
            )
        )

    async def command_swap(self, data, data_string, message):
        if not message.author.server_permissions.manage_server:
            return log.debug("Permission denied")  # No perms

        if len(data) < 2:
            return await self.send_message(
                message.channel, "{} Usage: `swap \"<section name>\" \"<section name>\"`".format(message.author.mention)
            )

        left, right = data[0], data[1]

        if not self.data_manager.has_section(message.server, left):
            return await self.send_message(
                message.channel, "{} No such section: `{}`\n\nPerhaps you meant to surround the section name with "
                                 "\"quotes\"?".format(message.author.mention, left)
            )

        if not self.data_manager.has_section(message.server, right):
            return await self.send_message(
                message.channel, "{} No such section: `{}`\n\nPerhaps you meant to surround the section name with "
                                 "\"quotes\"?".format(message.author.mention, right)
            )

        self.data_manager.swap_sections(message.server, left, right)
        self.data_manager.save_server(message.server.id)

        await self.send_message(
            message.channel,
            "{} Sections swapped: `{}` and `{}`\n\nRun the `update` command to wipe the info channel and recreate"
            " with the new layout.".format(
                message.author.mention, left, right
            )
        )

    # Aliases

    command_add = command_create
    command_delete = command_remove

# endregion

    pass
