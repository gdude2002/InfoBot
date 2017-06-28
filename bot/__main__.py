# coding=utf-8
import sys
import logging

from bot.client import Client

__author__ = "Gareth Coles"

logging.basicConfig(
    format="%(asctime)s | %(name)s | [%(levelname)s] %(message)s",
    level=logging.DEBUG if "--debug" in sys.argv else logging.INFO
)

logger = logging.getLogger("discord")
logger.setLevel(logging.WARNING)
handler = logging.FileHandler(
    filename="output.log", encoding="utf-8", mode="w"
)
handler.setFormatter(
    logging.Formatter("%(asctime)s | %(name)s | [%(levelname)s] %(message)s")
)
logger.addHandler(handler)


def main():
    client = Client()
    client.run(client.get_token(), bot=False)

if __name__ == "__main__":
    main()
