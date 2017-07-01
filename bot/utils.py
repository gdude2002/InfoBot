# coding=utf-8

__author__ = "Gareth Coles"


def line_splitter(lines, max_size):
    finished_lines = []
    current_line = ""

    for line in lines:
        if len(current_line) + len(line) + 2 >= max_size:
            if not current_line:
                raise ValueError("Encountered a line longer than {} characters".format(max_size))

            finished_lines.append(current_line)
            current_line = ""

        current_line += "\n{}".format(line)

    if current_line:
        finished_lines.append(current_line)

    return finished_lines
