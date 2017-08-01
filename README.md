InfoBot
=======

InfoBot is a Discord bot designed for managing the read-only server information channels
that you often see and need. 

Some types of information channel require updating from time to time, and doing so can be 
tricky as in some cases you need to delete half of the messages there just to add a section.

InfoBot is designed with channels like that in mind - although you can easily use it to manage
more static channels too.

For user documentation, please see [the wiki](https://github.com/gdude2002/InfoBot/wiki).

You can also chat with us [on Discord](https://discord.gg/ZUVSbah).

---

* Install Python 3.6 or later
* Set up a Virtualenv if you're using this in production
* `python -m pip install -r requirements.txt`
* Copy `config.yml.example` to `config.yml` and fill it out
* `python -m bot`
    * `--debug` for debug-level logging
    * `--no-log-discord` to prevent log messages from being relayed to Discord
        * Note that `DEBUG`-level messages and messages from the `asyncio` logger are never relayed to Discord
