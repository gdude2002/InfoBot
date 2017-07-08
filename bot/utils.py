# coding=utf-8

__author__ = "Gareth Coles"


def line_splitter(lines, max_size, split_only=False):
    finished_lines = []
    current_line = ""

    if not split_only:
        for line in lines:
            if len(current_line) + len(line) + 2 >= max_size:
                if not current_line:
                    raise ValueError("Encountered a line longer than {} characters".format(max_size))

                finished_lines.append(current_line)
                current_line = ""

            current_line += "\n{}".format(line)

        if current_line:
            finished_lines.append(current_line)
    else:
        for line in lines:
            current_line = line

            while len(current_line) + 2 >= max_size:
                finished_lines.append(current_line[:max_size-2])
                current_line = current_line[max_size-2:]
            else:
                finished_lines.append(current_line)

    return finished_lines
