# coding=utf-8
from logging import Handler, INFO, LogRecord, DEBUG

import sys

from bot.client import Client

__author__ = "Gareth Coles"


class DiscordLogHandler(Handler):
    def __init__(self, client: Client, level=INFO):
        super().__init__(level=level)
        self.client = client

    def emit(self, record: LogRecord):
        if record.levelno <= DEBUG:
            return

        if record.name == "asyncio":
            return

        if self.client.is_closed:
            return

        try:
            self.client.log_to_channel(record)
        except Exception as e:
            print("Failed to send log entry to Discord: {}".format(e), file=sys.stderr)
