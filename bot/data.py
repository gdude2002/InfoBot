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

HELP_TEXT = """

"""

SECTION_TYPES = {
    "text": TextSection,
    "faq": FAQSection
}

SECTION_TYPES.update({v: k for k, v in SECTION_TYPES.items()})

SECTION_REGEX = re.compile(r"[\d]+[\\/]?")

DEFAULT_CONFIG = {
    "control_chars": "->",
    "info_channel": None,
    "update_immediately": False
}

DEFAULT_SECTIONS = [
    ["help", "text", TextSection("help", HELP_TEXT).to_dict()]
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
            if not os.path.exists("data/{}".format(server_id)):
                self.add_server(server_id)

            with open("data/{}/config.yml".format(server_id), "w") as config_fh:
                yaml.safe_dump(data["config"], config_fh)

            with open("data/{}/sections.yml".format(server_id), "w") as sections_fh:
                yaml.safe_dump(self.serialise_sections(data["sections"]), sections_fh)

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
            loaded_sections.append(SECTION_TYPES[section_type].from_dict(name, data))

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
