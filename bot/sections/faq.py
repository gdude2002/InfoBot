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
    def __init__(self, name, questions=None):
        super().__init__(name)

        self.questions = questions or []

    def process_command(self, command, data, client, message) -> str:
        if command == "add":
            if " || " not in data:
                return "Syntax: `Question here || Answer here`"

            question, answer = data.split(" || ", 1)

            if self.has_question(question):
                return "Question already exists: `{}`".format(question)

            if len(MESSAGE_FORMAT.format(question, answer)) > 1000:
                return "Question and answer must be shorter than {} characters.".format(999 - len(MESSAGE_FORMAT))

            self.set_question(question, answer)
            client.sections_updated(message.server)

            return "Question added: `{}`".format(question)
        elif command == "delete":
            if not self.has_question(data):
                return "No such question: `{}`".format(data)
            self.delete_question(data)
            client.sections_updated(message.server)

            return "Question deleted: `{}`".format(data)
        elif command == "set":
            if " || " not in data:
                return "Syntax: `Question here || Answer here`"

            question, answer = data.split(" || ", 1)

            has_question = self.has_question(question)

            if len(MESSAGE_FORMAT.format(question, answer)) > 1000:
                return "Question and answer must be shorter than {} characters.".format(999 - len(MESSAGE_FORMAT))

            self.set_question(question, answer)
            client.sections_updated(message.server)

            if has_question:
                return "Question overwritten: `{}`".format(question)
            return "Question added: `{}`".format(question)
        return "Unknown command: {}".format(command)

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

    def render(self) -> List[str]:
        return [MESSAGE_FORMAT.format(question, answer) for question, answer in self.questions]

    def to_dict(self) -> dict:
        return {
            "questions": self.questions
        }
    
    @staticmethod
    def from_dict(name, data) -> "FAQSection":
        return FAQSection(name, **data)