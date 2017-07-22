# coding=utf-8
from typing import List

from bot.sections.base import BaseSection
from bot.utils import line_splitter

__author__ = "Gareth Coles"


class NumberedListSection(BaseSection):
    _type = "numbered_list"

    def __init__(self, name, items=None, template="**`{0})`** {1}", header="", footer=""):
        super().__init__(name, header=header, footer=footer)

        self.template = template
        self.items = items or []

    async def process_command(self, command, data, data_string, client, message) -> str:
        if command == "add":
            if len(data) < 1:
                return "Usage: `add \"<List Item>\" \"[List Item ...]\"`"

            added = 0
            too_long = []

            for i, item in enumerate(data):
                if len(item) > 200:
                    too_long.append(i)

                if item:
                    self.items.append(item)
                    added += 1

            client.sections_updated(message.server)

            if len(data) > 1:
                message = "{} list items added".format(added)

                if too_long:
                    message += "\n\nList items must be shorter than 200 characters. " \
                               "The following items were too long: `{}`".format(", ".join(too_long))

                return message
            else:
                return "List item added"
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
        elif command == "set":
            if len(data) < 2:
                return "Usage: `set <index> \"<data>\"`\n\nNote that indexes start at `1`"

            try:
                left, right = int(data[0]) - 1, data[1]
            except Exception:
                return "Usage: `swap <index> \"<data>\"`\n\nNote that indexes start at `1`"

            if left >= len(self.items) or left < 0:
                return "Unknown index: `{}`\n\nNote that indexes start at `1`".format(data[0])

            if len(right) > 200:
                return "List items must be shorter than 200 characters."

            self.items[left] = right

            client.sections_updated(message.server)
            return "Item at index `{}` set to `{}`".format(left, right)
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
                template.format("1", "Item Goes Here")
            except Exception:
                return "Invalid template. Ensure it contains `{0}` to be replaced with the list item's index, and " \
                       "`{1}` to be replaced with the list item."

            self.template = template

            client.sections_updated(message.server)
            return "Item template has been updated."

        return "Unknown command: `{}`\n\nAvailable commands: `add`, `remove`, `set`, `swap`, `template`".format(command)

    async def render(self) -> List[str]:
        return line_splitter([self.template.format(i + 1, line) for i, line in enumerate(self.items)], 2000)

    async def show(self) -> List[str]:
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
    def from_dict(name, data) -> "NumberedListSection":
        return NumberedListSection(name, **data)
