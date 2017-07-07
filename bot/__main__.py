# coding=utf-8
import sys
import logging

from bot.client import Client
from bot.log_handler import DiscordLogHandler

__author__ = "Gareth Coles"


def main():
    client = Client()

    file_handler = logging.FileHandler(
        filename="output.log", encoding="utf-8", mode="w"
    )

    if "--no-log-discord" in sys.argv:
        handlers = [file_handler, logging.StreamHandler()]
    else:
        handlers = [DiscordLogHandler(client), file_handler, logging.StreamHandler()]

    logging.basicConfig(
        format="%(asctime)s | %(name)10s | %(levelname)8s | %(message)s",
        level=logging.DEBUG if "--debug" in sys.argv else logging.INFO,
        handlers=handlers
    )

    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("websockets.protocol").setLevel(logging.INFO)

    client.run(client.get_token(), bot=True)


if __name__ == "__main__":
    main()
