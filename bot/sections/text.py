# coding=utf-8
from typing import List

from bot.sections.base import BaseSection

__author__ = "Gareth Coles"

SUPPORTED_COMMANDS = ["set"]


class TextSection(BaseSection):
    def __init__(self, name, text=None):
        super().__init__(name)

        self.text = text or ""

    def process_command(self, command, data, client, message) -> str:
        if command == "set":
            if len(data[0]) < 1000:
                self.text = data[0]
                return "Section data set"
            return "Section data must be less than 1000 characters"

        return "Unknown command: {}".format(command)

    def render(self) -> List[str]:
        return [self.text]

    def to_dict(self) -> dict:
        return {
            "text": self.text
        }
    
    @staticmethod
    def from_dict(name, data) -> "TextSection":
        return TextSection(name, **data)
