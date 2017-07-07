# coding=utf-8
from typing import List

from bot.sections.base import BaseSection

__author__ = "Gareth Coles"

MESSAGE_FORMAT = """
**Q**: *{}*

**A**: {}
__\_\_\_\_\_\_\_\_\_\___
"""


class FAQSection(BaseSection):
    _type = "faq"

    def __init__(self, name, questions=None, header="", footer=""):
        super().__init__(name, header=header, footer=footer)

        self.questions = questions or []

    def process_command(self, command, data, data_string, client, message) -> str:
        if command == "add":
            if len(data) < 2:
                return "Usage: `add \"<question>\" \"<answer>\"`"

            question, answer = data[0], data[1]

            if self.has_question(question):
                return "Question already exists: `{}`".format(question)

            if len(MESSAGE_FORMAT.format(question, answer)) > 2000:
                return "Question and answer must be shorter than {} characters.".format(1999 - len(MESSAGE_FORMAT))

            self.set_question(question, answer)
            client.sections_updated(message.server)

            return "Question added: `{}`".format(question)
        elif command == "remove":
            if len(data) < 1:
                return "Usage: `remove \"<question>\"`"

            question = data[0]

            if not self.has_question(question):
                return "No such question: `{}`".format(question)
            self.delete_question(question)
            client.sections_updated(message.server)

            return "Question deleted: `{}`".format(question)
        elif command == "set":
            if len(data) < 2:
                return "Usage: `set \"<question>\" \"<answer>\"`"

            question, answer = data[0], data[1]

            has_question = self.has_question(question)

            if len(MESSAGE_FORMAT.format(question, answer)) > 2000:
                return "Question and answer must be shorter than {} characters.".format(1999 - len(MESSAGE_FORMAT))

            self.set_question(question, answer)
            client.sections_updated(message.server)

            if has_question:
                return "Question overwritten: `{}`".format(question)
            return "Question added: `{}`".format(question)
        elif command == "swap":
            if len(data) < 2:
                return "Usage: `swap \"<question>\" \"<question>\"`"

            left, right = data[0], data[1]

            if not self.has_question(left):
                return "Unknown question: `{}`".format(left)

            if not self.has_question(right):
                return "Unknown question: `{}`".format(right)

            self.swap_questions(left, right)

            client.sections_updated(message.server)
            return "Question positions swapped successfully"
        return "Unknown command: {}\n\nAvailable commands: `add`, `remove`, `set`, `swap`".format(command)

    def has_question(self, question):
        for q, _ in self.questions:
            if question.lower() == q.lower():
                return True

        return False

    def set_question(self, question, answer):
        for question_tuple in self.questions:
            if question_tuple[0].lower() == question.lower():
                question_tuple[1] = answer
                return

        self.questions.append((question, answer))

    def delete_question(self, question):
        for i, q in enumerate(self.questions):
            if q[0].lower() == question.lower():
                self.questions.pop(i)
                return

    def swap_questions(self, left, right):
        left_index = -1
        right_index = -1

        for i, q in enumerate(self.questions):
            question = q[0].lower()
            if question == left.lower():
                left_index = i
                continue

            if question == right.lower():
                right_index = i
                continue

        if left_index >= 0 and right_index >= 0:
            self.questions[left_index], self.questions[right_index] = self.questions[right_index], \
                                                                      self.questions[left_index]

    def render(self) -> List[str]:
        return [MESSAGE_FORMAT.format(question, answer) for question, answer in self.questions]

    def show(self) -> List[str]:
        commands = []

        for question, answer in self.questions:
            commands.append("{}" + "add \"{}\" \"{}\"".format(question, answer))

        return commands

    def to_dict(self) -> dict:
        return {
            "questions": self.questions,
            "header": self.header,
            "footer": self.footer
        }

    @staticmethod
    def from_dict(name, data) -> "FAQSection":
        return FAQSection(name, **data)
