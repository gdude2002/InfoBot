# coding=utf-8
import datetime
import io
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

GIST_CREATE_URL = "https://api.github.com/gists"
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

            if hasattr(self, "command_{}".format(command.replace("-", "_"))):
                await getattr(self, "command_{}".format(command.replace("-", "_")))(data, args_string, message)

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

    def has_permission(self, user):
        if user.server_permissions.manage_server:
            return True
        elif int(user.id) == int(self.config["owner_id"]):
            return True

        return False

    def has_permission_notes(self, user):
        if user.server_permissions.manage_messages:
            return True
        elif int(user.id) == int(self.config["owner_id"]):
            return True

        return False

    def create_note_embed(self, server, note, index):
        embed = Embed(
            title="{}: {}".format(note["status"].title(), index),
            description=note["text"],
            timestamp=note["submitted"]
        )

        if note["status"] == "open":
            colour = Colour.blue()
        elif note["status"] == "closed":
            colour = Colour.gold()
        else:
            colour = Colour.green()

        embed.colour = colour

        user = server.get_member(note["submitter"]["id"])

        if user:
            embed.set_footer(text=user.name, icon_url=(user.avatar_url or user.default_avatar_url))
        else:
            embed.set_footer(text=note["submitter"]["name"])

        return embed

    # region Commands

    async def command_config(self, data, data_string, message):
        if not self.has_permission(message.author):
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
        if not self.has_permission(message.author):
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
        if not self.has_permission(message.author):
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
        if not self.has_permission(message.author):
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
            result = await section.process_command(command, data, data_string, self, message)
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
        if not self.has_permission(message.author):
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

    async def command_show(self, data, data_string, message):
        if not self.has_permission(message.author):
            return log.debug("Permission denied")  # No perms

        await self.send_message(
            message.channel, "{} Just a moment, collecting and uploading data...".format(message.author.mention)
        )

        content = """
Rendered Markdown
=================

{}

Command Breakdown
=================

{}
        """

        markdown = []
        commands = []

        sections = self.data_manager.get_sections(message.server)
        chars = self.data_manager.get_server_command_chars(message.server)

        for name, section in sections:
            markdown_set = ["**__{}__**".format(name)]
            command_set = ["add {} \"{}\"".format(section._type, name)]

            if section.get_header():
                command_set.append("header \"{}\" \"{}\"".format(name, section.get_header()))
                markdown_set.append(section.get_header())

            for x in await section.show():
                command_set.append(x)

            for part in await section.render():
                markdown_set.append(part)

            if section.get_footer():
                command_set.append("footer \"{}\" \"{}\"".format(name, section.get_footer()))
                markdown_set.append(section.get_footer())

            commands.append(command_set)
            markdown.append(markdown_set)

            final_markdown = []
            final_commands = []

        for m_set in markdown:
            final_markdown.append("\n\n".join(m_set))

        for c_set in commands:
            final_commands.append("\n\n".join([
                chars + c for c in c_set
            ]))

        content = content.format(
            "\n\n---\n\n".join(final_markdown),
            "\n\n---\n\n".join(final_commands),
        )

        del markdown, commands
        del final_markdown, final_commands

        await self.send_file(
            message.channel, io.BytesIO(content.encode("UTF-8")), filename="data.txt",
            content="{} Here's the data you requested.".format(message.author.mention)
        )

    async def command_update(self, data, data_string, message):
        if not self.has_permission(message.author):
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
            await asyncio.sleep(0.2)

            if section.get_header():
                await self.send_message(channel, section.get_header())
                await asyncio.sleep(0.2)

            for part in await section.render():
                await self.send_message(channel, part)
                await asyncio.sleep(0.2)

            if section.get_footer():
                await self.send_message(channel, section.get_footer())
                await asyncio.sleep(0.2)

        await self.send_message(
            message.channel,
            "{} The info channel has been updated!".format(
                message.author.mention
            )
        )

    async def command_swap(self, data, data_string, message):
        if not self.has_permission(message.author):
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

    async def command_header(self, data, data_string, message):
        if not self.has_permission(message.author):
            return log.debug("Permission denied")  # No perms

        if len(data) < 2:
            return await self.send_message(
                message.channel, "{} Usage: `header \"<section name>\" \"<data>\"`".format(message.author.mention)
            )

        section_name, header = data[0], data[1]

        if not self.data_manager.get_section(message.server, section_name):
            return await self.send_message(
                message.channel, "{} No such section: `{}`\n\nPerhaps you meant to surround the section name with "
                                 "\"quotes\"?".format(message.author.mention, section_name)
            )

        if len(header) > 2000:
            return await self.send_message(
                message.channel, "{} Section header must be less than 2000 characters in length"
            )

        self.data_manager.get_section(message.server, section_name).set_header(header)

        await self.send_message(
            message.channel,
            "{} Section header updated: `{}`\n\nRun the `update` command to wipe the info channel and recreate with "
            "it.".format(
                message.author.mention, section_name
            )
        )

    async def command_footer(self, data, data_string, message):
        if not self.has_permission(message.author):
            return log.debug("Permission denied")  # No perms

        if len(data) < 2:
            return await self.send_message(
                message.channel, "{} Usage: `footer \"<section name>\" \"<data>\"`".format(message.author.mention)
            )

        section_name, footer = data[0], data[1]

        if not self.data_manager.get_section(message.server, section_name):
            return await self.send_message(
                message.channel, "{} No such section: `{}`\n\nPerhaps you meant to surround the section name with "
                                 "\"quotes\"?".format(message.author.mention, section_name)
            )

        if len(footer) > 2000:
            return await self.send_message(
                message.channel, "{} Section footer must be less than 2000 characters in length"
            )

        self.data_manager.get_section(message.server, section_name).set_footer(footer)

        await self.send_message(
            message.channel,
            "{} Section footer updated: `{}`\n\nRun the `update` command to wipe the info channel and recreate with "
            "it.".format(
                message.author.mention, section_name
            )
        )

    # Notes commands

    async def command_setup_notes(self, data, data_string, message):
        if not self.has_permission(message.author):
            return log.debug("Permission denied")  # No perms

        if len(data) > 1:
            return await self.send_message(
                message.channel,
                content="{} Usage: `setup-notes <channel ID>`".format(message.author.mention)
            )

        try:
            channel = self.get_channel(str(int(data[0])))
        except Exception:
            return await self.send_message(
                message.channel,
                content="{} Command usage: `setup-notes <channel ID>`".format(message.author.mention)
            )

        if channel not in message.server.channels:
            return await self.send_message(
                message.channel,
                content="{} Unable to find channel for ID `{}`".format(message.author.mention, data[0])
            )

        self.data_manager.set_notes_channel(message.server, channel)

        await self.send_message(
            message.channel,
            content="{} Notes channel set to {}\n\nRun the `update-notes` command to wipe and fill it if you're "
                    "moving channel (rather than setting up for the first time)".format(message.author.mention,
                                                                                        channel.mention)
        )

    async def command_update_notes(self, data, data_string, message):
        if not self.has_permission(message.author):
            return log.debug("Permission denied")  # No perms

        channel = self.data_manager.get_notes_channel(message.server)

        if not channel:
            return await self.send_message(
                message.channel,
                "{} No notes channel has been set for this server. Try the `setup-notes` command!".format(
                    message.author.mention
                )
            )

        channel = self.get_channel(channel)

        if not channel:
            return await self.send_message(
                message.channel,
                "{} The configured notes channel no longer exists. Set another with the `setup-notes` command!".format(
                    message.author.mention
                )
            )

        await self.clear_channel(channel)

        notes = self.data_manager.get_notes(message.server)

        for index, note in notes.items():
            sent_message = await self.send_message(
                channel, embed=self.create_note_embed(message.server, note, index)
            )

            note["message_id"] = sent_message.id

        await self.send_message(
            message.channel,
            "{} The notes channel has been updated!".format(
                message.author.mention
            )
        )

    async def command_note(self, data, data_string, message):
        if not self.has_permission_notes(message.author):
            return log.debug("Permission denied")  # No perms

        if len(data) < 1:
            return await self.send_message(
                message.channel, "{} Usage: `note \"<text>\"`".format(message.author.mention)
            )

        text = data[0]

        index, note = self.data_manager.create_note(message.server, message, text)
        self.data_manager.save_server(message.server.id)

        channel = self.data_manager.get_notes_channel(message.server)

        if channel:
            sent_message = await self.send_message(
                self.get_channel(channel),
                embed=self.create_note_embed(message.server, note, index)
            )

            note["message_id"] = sent_message.id

            await self.send_message(
                message.channel,
                "{} Note created: `{}`".format(
                    message.author.mention, index
                )
            )
        else:
            await self.send_message(
                message.channel,
                "{} Note created: `{}`\n\n**Warning**: No notes channel has been set up. Try the `setup-notes` "
                "command!".format(
                    message.author.mention, index
                )
            )

    async def command_reopen(self, data, data_string, message):
        if not self.has_permission_notes(message.author):
            return log.debug("Permission denied")  # No perms

        if len(data) < 1:
            return await self.send_message(
                message.channel, "{} Usage: `reopen \"<note number>\"`".format(message.author.mention)
            )

        index = data[0]

        note = self.data_manager.get_note(message.server, index)

        if not note:
            return await self.send_message(
                message.channel, "{} Unknown note ID: {}".format(message.author.mention, index)
            )

        if note["status"] == "open":
            return await self.send_message(
                message.channel, "{} That note is already open!".format(message.author.mention)
            )

        note["status"] = "open"
        self.data_manager.save_server(message.server.id)

        channel = self.data_manager.get_notes_channel(message.server)

        if channel:
            try:
                note_message = await self.get_message(self.get_channel(channel), note["message_id"])
            except discord.NotFound:
                note_message = None

            if not note_message:
                return await self.send_message(
                    message.channel,
                    "{} Note updated: `{}`\n\n**Warning**: The message containing this note has been deleted. Use the "
                    "`update-notes` command to repopulate the notes channel!".format(
                        message.author.mention, index
                    )
                )

            await self.edit_message(
                note_message, embed=self.create_note_embed(message.server, note, index)
            )

            await self.send_message(
                message.channel,
                "{} Note updated: `{}`".format(
                    message.author.mention, index
                )
            )
        else:
            await self.send_message(
                message.channel,
                "{} Note updated: `{}`\n\n**Warning**: No notes channel has been set up. Try the `setup-notes` "
                "command!".format(
                    message.author.mention, index
                )
            )

    async def command_resolve(self, data, data_string, message):
        if not self.has_permission_notes(message.author):
            return log.debug("Permission denied")  # No perms

        if len(data) < 1:
            return await self.send_message(
                message.channel, "{} Usage: `resolve \"<note number>\"`".format(message.author.mention)
            )

        index = data[0]

        note = self.data_manager.get_note(message.server, index)

        if not note:
            return await self.send_message(
                message.channel, "{} Unknown note ID: {}".format(message.author.mention, index)
            )

        if note["status"] == "resolved":
            return await self.send_message(
                message.channel, "{} That note is already resolved!".format(message.author.mention)
            )

        note["status"] = "resolved"
        self.data_manager.save_server(message.server.id)

        channel = self.data_manager.get_notes_channel(message.server)

        if channel:
            try:
                note_message = await self.get_message(self.get_channel(channel), note["message_id"])
            except discord.NotFound:
                note_message = None

            if not note_message:
                return await self.send_message(
                    message.channel,
                    "{} Note updated: `{}`\n\n**Warning**: The message containing this note has been deleted. Use the "
                    "`update-notes` command to repopulate the notes channel!".format(
                        message.author.mention, index
                    )
                )

            await self.edit_message(
                note_message, embed=self.create_note_embed(message.server, note, index)
            )

            await self.send_message(
                message.channel,
                "{} Note updated: `{}`".format(
                    message.author.mention, index
                )
            )
        else:
            await self.send_message(
                message.channel,
                "{} Note updated: `{}`\n\n**Warning**: No notes channel has been set up. Try the `setup-notes` "
                "command!".format(
                    message.author.mention, index
                )
            )

    async def command_close(self, data, data_string, message):
        if not self.has_permission_notes(message.author):
            return log.debug("Permission denied")  # No perms

        if len(data) < 1:
            return await self.send_message(
                message.channel, "{} Usage: `close \"<note number>\"`".format(message.author.mention)
            )

        index = data[0]

        note = self.data_manager.get_note(message.server, index)

        if not note:
            return await self.send_message(
                message.channel, "{} Unknown note ID: {}".format(message.author.mention, index)
            )

        if note["status"] == "closed":
            return await self.send_message(
                message.channel, "{} That note is already closed!".format(message.author.mention)
            )

        note["status"] = "closed"
        self.data_manager.save_server(message.server.id)

        channel = self.data_manager.get_notes_channel(message.server)

        if channel:
            try:
                note_message = await self.get_message(self.get_channel(channel), note["message_id"])
            except discord.NotFound:
                note_message = None

            if not note_message:
                return await self.send_message(
                    message.channel,
                    "{} Note updated: `{}`\n\n**Warning**: The message containing this note has been deleted. Use the "
                    "`update-notes` command to repopulate the notes channel!".format(
                        message.author.mention, index
                    )
                )

            await self.edit_message(
                note_message, embed=self.create_note_embed(message.server, note, index)
            )

            await self.send_message(
                message.channel,
                "{} Note updated: `{}`".format(
                    message.author.mention, index
                )
            )
        else:
            await self.send_message(
                message.channel,
                "{} Note updated: `{}`\n\n**Warning**: No notes channel has been set up. Try the `setup-notes` "
                "command!".format(
                    message.author.mention, index
                )
            )

    # Aliases

    command_add = command_create
    command_delete = command_remove

# endregion

    pass
