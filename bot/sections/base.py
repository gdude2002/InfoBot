# coding=utf-8
from typing import List

__author__ = "Gareth Coles"


class BaseSection:
    def __init__(self, name):
        self.name = name

    def render(self) -> List[str]:
        pass

    def to_dict(self) -> dict:
        pass

    def process_command(self, command, data, client, message) -> str:
        return "Not Implemented"

    @staticmethod
    def from_dict(name, data) -> "BaseSection":
        pass
