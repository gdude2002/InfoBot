# coding=utf-8
from collections import OrderedDict
from typing import List

from bot.sections.base import BaseSection

__author__ = "Gareth Coles"

MESSAGE_FORMAT = """
**__{}__**

{}
"""


class FAQSection(BaseSection):
    def __init__(self, name, questions=None):
        super().__init__(name)

        self.questions = questions or OrderedDict()

    def process_command(self, command, data, client, message) -> str:
        return "Not Implemented"

    def render(self) -> List[str]:
        return [MESSAGE_FORMAT.format(question, answer) for question, answer in self.questions]

    def to_dict(self) -> dict:
        return {
            "questions": self.questions
        }
    
    @staticmethod
    def from_dict(name, data) -> "FAQSection":
        return FAQSection(name, **data)
