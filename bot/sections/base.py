# coding=utf-8
from typing import List

__author__ = "Gareth Coles"


class BaseSection:
    def __init__(self, name, header="", footer=""):
        self.name = name
        self.header = header
        self.footer = footer

    def render(self) -> List[str]:
        pass

    def to_dict(self) -> dict:
        pass

    def set_header(self, header):
        self.header = header

    def set_footer(self, footer):
        self.footer = footer

    def get_header(self) -> str:
        return self.header

    def get_footer(self) -> str:
        return self.footer

    def process_command(self, command, data, data_string, client, message) -> str:
        return "Not Implemented"

    @staticmethod
    def from_dict(name, data) -> "BaseSection":
        pass
