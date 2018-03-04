# coding=utf-8
from code import InteractiveInterpreter

__author__ = 'Gareth Coles'

CODE_TEMPLATE = """
async def _func():
{}
"""


class Interpreter(InteractiveInterpreter):
    write_callable = None

    def __init__(self, locals, bot):
        locals["bot"] = bot
        super().__init__(locals)

        self.locals["print"] = self.write

    async def runsource(self, code, message, *args, **kwargs):
        self.locals["_rvalue"] = []
        self.locals["message"] = message

        lines = []
        for line in code.split("\n"):
            lines.append("    {}".format(line))

        code = "\n".join(lines)
        code = CODE_TEMPLATE.format(code)

        print(code)

        super().runsource(code, *args, **kwargs)
        super().runsource("_rvalue = _func()", *args, **kwargs)

        rvalue = await self.locals.get("_rvalue")

        if "_rvalue" in self.locals:
            del self.locals["_rvalue"]

        return rvalue

    def set_output(self, func):
        self.write_callable = func

    def write(self, data):
        self.write_callable(str(data))