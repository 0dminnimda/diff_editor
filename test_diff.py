import difflib
import my_diff_lib
import webbrowser
import os
import sys

prefix = "adf\n"*15

text1 = prefix + """
This is the first line.
This line is the same in both.
This line is unique to the first text.


hgbtoot skjpsdfkpaskdfjp hasdfjkaspd
End
End End End
End End

gotcha!

real end
"""

text2 = prefix + """
This is the first line, but with a change.
This line is the same in both.

This line is unique to the second text.


And here is an extra line.


End
End End End
End End
real end
"""

# print(text1)
# print(text2)

lines1 = text1.splitlines()
lines2 = text2.splitlines()

RED_BG = "\033[41m"
GREEN_BG = "\033[42m"
YELLOW_BG = "\033[43m"
RED_FG = "\033[91m"
GREEN_FG = "\033[92m"
RESET = "\033[0m"

for n1, n2, changed in my_diff_lib.mdiff(lines1, lines2):
    p1 = RED_BG if changed else ""
    s1 = (n1 or "").ljust(50)
    s1 = p1 + s1 if n1 is not None else YELLOW_BG + s1

    p2 = GREEN_BG if changed else ""
    s2 = (n2 or "").ljust(50)
    s2 = p2 + s2 if n2 is not None else YELLOW_BG + s2

    # similar = False
    # s = list(SequenceMatcher(isjunk=difflib.IS_CHARACTER_JUNK, a=n1, b=n2).generate_opcodes())
    # intra = my_diff_lib._get_intra_line_opcodes(n1, n2) if similar else []
    print(f"{s1}{RESET}|{s2}{RESET}")


import fast_diff_match_patch


opcodes = fast_diff_match_patch.diff(text1, text2, timelimit=0.1, checklines=True, counts_only=False)
print(opcodes)


def generate_side_by_side_lines(opcodes):
    """
    A generator that takes character-level opcodes from fast_diff_match_patch
     and yields pairs of completed, colored, side-by-side lines.
    """
    left_line_parts = []
    right_line_parts = []

    for kind, text in opcodes:
        # Split the text by newlines. The parts list will contain the content
        # between newlines. The number of newlines is len(parts) - 1.
        parts = text.split('\n')

        for i, part in enumerate(parts):
            # If the part is not empty, add it to the correct column(s)
            if part:
                if kind == '=':
                    left_line_parts.append(part)
                    right_line_parts.append(part)
                elif kind == '-':
                    left_line_parts.append(f"{RED_BG}{part}{RESET}")
                elif kind == '+':
                    right_line_parts.append(f"{GREEN_BG}{part}{RESET}")

            # If this is not the last part, it means a newline was here.
            # This completes a line, so we yield the result and reset.
            if i < len(parts) - 1:
                yield ("".join(left_line_parts), "".join(right_line_parts))
                left_line_parts = []
                right_line_parts = []

    # After the loop, there might be a final, non-terminated line. Yield it.
    if left_line_parts or right_line_parts:
        yield ("".join(left_line_parts), "".join(right_line_parts))


LINE_WIDTH = 50
EMPTY_LINE = " "*LINE_WIDTH
for left_line, right_line in generate_side_by_side_lines(opcodes):
    # Pad strings that have ANSI codes correctly by calculating visible length
    def visible_len(s):
        return len(s) - (s.count(RESET) * (len(RED_BG) + len(RESET)))

    # Fallback for simple cases where one side is completely empty
    if left_line is None:
        left_display = f"{YELLOW_BG}{EMPTY_LINE}{RESET}"
    else:
        padding = " " * (LINE_WIDTH - visible_len(left_line))
        left_display = f"{left_line}{padding}"

    if right_line is None:
        right_display = f"{YELLOW_BG}{EMPTY_LINE}{RESET}"
    else:
        padding = " " * (LINE_WIDTH - visible_len(right_line))
        right_display = f"{right_line}{padding}"

    print(f"{left_display}|{right_display}")
