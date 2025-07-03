import difflib
import my_diff_lib
import webbrowser
import os

prefix = "adf\n"*15

text1 = prefix + """
This is the first line.
This line is the same in both.
This line is unique to the first text.


hgbtoot skjpsdfkpaskdfjp hasdfjkaspd
End

gotcha!

real end
"""

text2 = prefix + """
This is the first line, but with a change.
This line is the same in both.

This line is unique to the second text.


And here is an extra line.


End
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

for n1, n2, changed, similar in my_diff_lib.mdiff(lines1, lines2):
    p1 = RED_BG if changed else ""
    s1 = (n1 or "").ljust(50)
    s1 = p1 + s1 if n1 is not None else YELLOW_BG + s1

    p2 = GREEN_BG if changed else ""
    s2 = (n2 or "").ljust(50)
    s2 = p2 + s2 if n2 is not None else YELLOW_BG + s2

    intra = my_diff_lib._get_intra_line_opcodes(n1, n2) if similar else []
    print(f"{s1}{RESET}|{s2}{RESET}  {intra}")


# import fast_diff_match_patch
#
# opcodes = fast_diff_match_patch.diff(text1, text2, timelimit=0.1, checklines=True, counts_only=False)
# print(opcodes)
#
# print(fast_diff_match_patch.match(text1, text2))
