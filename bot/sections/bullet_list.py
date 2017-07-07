# coding=utf-8
from typing import List

from bot.sections.base import BaseSection
from bot.utils import line_splitter

__author__ = "Gareth Coles"


class BulletedListSection(BaseSection):
    _type = "bulleted_list"

    def __init__(self, name, items=None, template="\u2022 {0}", header="", footer=""):
        super().__init__(name, header=header, footer=footer)

        self.items = items or []
        self.template = template

    def process_command(self, command, data, data_string, client, message) -> str:
        if command == "add":
            if len(data) < 1:
                return "Usage: `add \"List Item\"`"

            if data[0] and len(data[0]) < 200:
                self.items.append(data[0])
                client.sections_updated(message.server)
                return "List item added"
            return "List items must be shorter than 200 characters"
        elif command == "remove":
            if not data:
                return "Usage: `delete <item index>`\n\nNote that indexes start at `1`"

            try:
                index = int(data[0]) - 1
            except:
                return "Usage: `delete <item index>`\n\nNote that indexes start at `1`"

            if index >= len(self.items):
                return "Unknown item: `{}`\n\nNote that indexes start at `1`".format(data[0])

            self.items.pop(index)
            client.sections_updated(message.server)
            return "Item at index `{}` removed".format(data[0])
        elif command == "swap":
            if len(data) < 2:
                return "Usage: `swap <index> <index>`\n\nNote that indexes start at `1`"

            try:
                left, right = int(data[0]) - 1, int(data[1]) - 1
            except Exception:
                return "Usage: `swap <index> <index>`\n\nNote that indexes start at `1`"

            if left >= len(self.items) or left < 0:
                return "Unknown index: `{}`\n\nNote that indexes start at `1`".format(data[0])

            if right >= len(self.items) or right < 0:
                return "Unknown index: `{}`\n\nNote that indexes start at `1`".format(data[1])

            self.items[left], self.items[right] = self.items[right], self.items[left]

            client.sections_updated(message.server)
            return "Items at indexes `{}` and `{}` swapped".format(data[0], data[1])
        elif command == "template":
            if not data:
                return "Here is the current template.\n\n```{}```".format(self.template)

            template = data[0]

            try:
                template.format("Item Goes Here")
            except Exception:
                return "Invalid template. Ensure it contains `{0}` to be replaced with the list item."

            self.template = template

            client.sections_updated(message.server)
            return "Item template has been updated."

        return "Unknown command: `{}`\n\nAvailable commands: `add`, `remove`, `swap`, `template`".format(command)

    def render(self) -> List[str]:
        return line_splitter([self.template.format(line) for line in self.items], 2000)

    def show(self) -> List[str]:
        commands = ["section \"{}\" template \"{}\"".format(self.name, self.template)]

        for line in self.items:
            commands.append("section \"{}\" add \"{}\"".format(self.name, line))

        return commands

    def to_dict(self) -> dict:
        return {
            "items": self.items,
            "template": self.template,
            "header": self.header,
            "footer": self.footer
        }

    @staticmethod
    def from_dict(name, data) -> "BulletedListSection":
        return BulletedListSection(name, **data)
