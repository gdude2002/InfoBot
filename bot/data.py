# coding=utf-8
import logging
import os
import re

from ruamel import yaml
from typing import List, Union

from bot.sections.base import BaseSection
from bot.sections.faq import FAQSection
from bot.sections.text import TextSection

__author__ = "Gareth Coles"

HELP_TEXT = [
    """
Congratulations, your info channel has been set up correctly! Here's a few tips on getting the most out of me.

• As a first step, you should `delete` this section and set up the sections that you want. This channel will not be \
updated until you run the `update` command, so ensure that you do that when you're ready. All changes are saved \
immediately, however.
• Make sure that you name your sections how you want them to display. This section is named `Welcome Message`, and \
that name is used as the title when your section is posted.
• Don't forget to use the `help` command if you need more information!

If you have any problems, feel free to head over to <https://github.com/gdude2002/InfoBot> and raise a ticket!
    """
]

SECTION_TYPES = {
    "text": TextSection,
    "faq": FAQSection
}

SECTION_TYPES.update({v: k for k, v in SECTION_TYPES.items()})

SECTION_REGEX = re.compile(r"[\d]+[\\/]?")

DEFAULT_CONFIG = {
    "control_chars": "!",
    "info_channel": None
}

DEFAULT_SECTIONS = [
    ["Welcome Message", "text", TextSection("help", HELP_TEXT).to_dict()]
]

log = logging.getLogger("Data")


class DataManager:
    # data = {
    #     server_id: {
    #         sections: [
    #             [name, object] (stored as name, type, data)
    #         ]
    #         config: {}
    #     }
    # }

    data = {}

    def __init__(self):
        if not os.path.exists("data"):
            os.mkdir("data")

    def load(self):
        for fn in os.listdir("data/"):
            if os.path.isdir("data/{}".format(fn)):
                if SECTION_REGEX.match(fn):
                    if fn[-1] in "\\/":
                        fn = fn[:-1]

                    try:
                        self.load_server(fn)
                    except Exception:
                        log.exception("Failed to load server: {}".format(fn))

    def save(self):
        for server_id, data in self.data.items():
            self.save_server(server_id, data)

    def save_server(self, server_id, data=None):
        if not data:
            data = self.data[server_id]

        try:
            if not os.path.exists("data/{}".format(server_id)):
                self.add_server(server_id)

            with open("data/{}/config.yml".format(server_id), "w") as config_fh:
                yaml.safe_dump(data["config"], config_fh)

            with open("data/{}/sections.yml".format(server_id), "w") as sections_fh:
                yaml.safe_dump(self.serialise_sections(data["sections"]), sections_fh)
        except Exception:
            log.exception("Error saving server '{}'".format(server_id))

    def load_server(self, server_id):
        if not os.path.exists("data/{}".format(server_id)):
            return False

        log.info("Loading server: {}".format(server_id))

        config = yaml.safe_load(open("data/{}/config.yml".format(server_id), "r"))
        sections = yaml.safe_load(open("data/{}/sections.yml".format(server_id), "r"))

        self.data[server_id] = {
            "config": config,
            "sections": self.load_sections(sections)
        }

        return True

    def load_sections(self, sections: List[Union[str, str, dict]]):
        loaded_sections = []

        for name, section_type, data in sections:
            loaded_sections.append(
                [name, SECTION_TYPES[section_type].from_dict(name, data)]
            )

        return loaded_sections

    def serialise_sections(self, sections: List[Union[str, BaseSection]]):
        unloaded_sections = []

        for name, section in sections:
            unloaded_sections.append([section.name, SECTION_TYPES[section.__class__], section.to_dict()])

        return unloaded_sections

    def add_server(self, server_id):
        if os.path.exists("data/{}".format(server_id)):
            return False

        os.mkdir("data/{}".format(server_id))

        with open("data/{}/config.yml".format(server_id), "w") as config_fh:
            yaml.safe_dump(DEFAULT_CONFIG, config_fh)

        with open("data/{}/sections.yml".format(server_id), "w") as sections_fh:
            yaml.safe_dump(DEFAULT_SECTIONS, sections_fh)

        self.data[server_id] = {
            "config": DEFAULT_CONFIG.copy(),
            "sections": self.load_sections(DEFAULT_SECTIONS)
        }

        log.info("Added server: {}".format(server_id))

        return True

    # Convenience functions

    def get_config(self, server):
        return self.data[server.id]["config"]

    def set_config(self, server, key, value):
        self.data[server.id]["config"][key] = value

    def add_section(self, server, section):
        self.data[server.id]["sections"].append([section.name, section])

    def remove_section(self, server, section):
        sections = self.data[server.id]["sections"]

        for i, section_tuple in enumerate(sections):
            if section_tuple[0].lower() == section.lower():
                sections.pop(i)
                return

    def get_section_class(self, section_type):
        return SECTION_TYPES.get(section_type.lower())

    def get_server_command_chars(self, server):
        return self.data[server.id]["config"]["control_chars"]

    def get_section(self, server, section):
        sections = self.data[server.id]["sections"]

        for name, s in sections:
            if name.lower() == section.lower():
                return s

        return None

    def get_sections(self, server):
        return self.data[server.id]["sections"]

    def get_channel(self, server):
        return self.data[server.id]["config"]["info_channel"]

    def set_channel(self, server, channel):
        self.data[server.id]["config"]["info_channel"] = channel.id
