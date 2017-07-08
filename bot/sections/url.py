# coding=utf-8
from typing import List

import aiohttp

from bot.sections.base import BaseSection
from bot.utils import line_splitter

__author__ = "Gareth Coles"


class URLSection(BaseSection):
    _type = "url"
    cached_lines = []

    def __init__(self, name, url=None, header="", footer=""):
        super().__init__(name, header=header, footer=footer)

        self.url = url or []

    async def process_command(self, command, data, data_string, client, message) -> str:
        if command == "set":
            if len(data) < 1:
                return "Usage: `set \"<url>\"`"

            url = data[0]

            if not url:
                return "Please supply a URL to retrieve text from"

            while url[0] in "`<" and url[-1] in "`>" and url[0] == url[-1]:
                url = url[1:-1]

            session = aiohttp.ClientSession()

            try:
                async with session.get(url, timeout=30) as resp:
                    text = await resp.text()
                self.cached_lines = self.split_paragraphs(text)
            except Exception as e:
                return "Failed to retrieve URL: `{}`".format(e)
            else:
                self.url = url
                client.sections_updated(message.server)
                return "URL set; retrieved `{}` messages' worth of text".format(len(self.cached_lines))
            finally:
                session.close()

        return "Unknown command: `{}`\n\nAvailable command: `set`".format(command)

    def split_paragraphs(self, text):
        parts = text.split("\n\n")
        return line_splitter(parts, 2000)

    async def render(self) -> List[str]:
        session = aiohttp.ClientSession()

        try:
            async with session.get(self.url, timeout=30) as resp:
                text = await resp.text()
            self.cached_lines = self.split_paragraphs(text)
        except Exception as e:
            return ["**ERROR**: Failed to retrieve URL `{}`: `{}`".format(self.url, e)]
        else:
            return self.cached_lines
        finally:
            session.close()

    async def show(self) -> List[str]:
        return [
            "section \"{}\" set \"{}\"".format(self.name, self.url)
        ]

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "header": self.header,
            "footer": self.footer
        }

    @staticmethod
    def from_dict(name, data) -> "URLSection":
        return URLSection(name, **data)
