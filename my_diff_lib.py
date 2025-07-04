import difflib
from enum import IntEnum, auto


class Tag(IntEnum):
    REPLACE = 0
    DELETE  = auto()
    INSERT  = auto()
    EQUAL   = auto()
    # SYNCH   = auto()
    COUNT   = auto()


REPLACE = Tag.REPLACE
DELETE  = Tag.DELETE
INSERT  = Tag.INSERT
EQUAL   = Tag.EQUAL
# SYNCH   = Tag.SYNCH
COUNT   = Tag.COUNT


class SequenceMatcher(difflib.SequenceMatcher):
    REFINE_CUTOFF = 0.75

    def generate_opcodes(self, refine: bool = False):
        i = j = 0
        for ai, bj, size in self.get_matching_blocks():
            tag = COUNT
            if i < ai and j < bj: tag = REPLACE
            elif i < ai:          tag = DELETE
            elif j < bj:          tag = INSERT

            if refine and tag == REPLACE:
                yield from self._refine_replace_block(i, ai, j, bj)
            elif tag != COUNT:
                yield (tag, i, ai, j, bj)

            i, j = ai+size, bj+size
            if size:
                yield (EQUAL, ai, i, bj, j)

    def _refine_replace_block(self, i1, i2, j1, j2):
        """
        A generator that recursively refines a 'REPLACE' block by operating
        on its indices, closely following the logic of `difflib.Differ._fancy_replace`.
        """

        # Base cases for recursion
        if i1 >= i2:
            if j1 < j2: yield (INSERT, i1, i1, j1, j2)
            return
        if j1 >= j2:
            if i1 < i2: yield (DELETE, i1, i2, j1, j1)
            return

        # don't synch up unless the lines have a similarity score of at
        # least cutoff; best_ratio tracks the best score seen so far
        best_ratio = self.REFINE_CUTOFF * 0.98  # `best_ratio` starts just under the cutoff
        best_i, best_j = -1, -1
        eqi, eqj = None, None   # 1st indices of equal lines (if any)

        # Create a single line-cruncher to be reused
        line_cruncher = difflib.SequenceMatcher(isjunk=difflib.IS_CHARACTER_JUNK)

        # Search for the best matching pair
        for j in range(j1, j2):
            line_cruncher.set_seq2(self.b[j])
            for i in range(i1, i2):
                if self.a[i] == self.b[j]:
                    if eqi is None:
                        eqi, eqj = i, j
                    continue
                line_cruncher.set_seq1(self.a[i])

                if line_cruncher.real_quick_ratio() <= best_ratio:
                    continue
                if line_cruncher.quick_ratio() <= best_ratio:
                    continue
                ratio = line_cruncher.ratio()
                if ratio > best_ratio:
                    best_ratio, best_i, best_j = ratio, i, j


        # Decide which synch point to use, if any
        if best_ratio < self.REFINE_CUTOFF:
            # No non-identical "pretty close" pair found.
            if eqi is None:
                # No identical pair either. Fallback to a plain replace.
                yield (REPLACE, i1, i2, j1, j2)
                return

            # No close pair, but an identical pair was found. Use it.
            best_i, best_j = eqi, eqj
        else:
            # there's a close pair, so forget the identical pair (if any)
            eqi = None


        # 1. Yield the refined opcodes for the block *before* the synch point
        yield from self._refine_replace_block(i1, best_i, j1, best_j)

        # 2. Yeild the synch line itself
        if eqi is None:
            yield REPLACE, best_i, best_i + 1, best_j, best_j + 1
        else:
            yield EQUAL, best_i, best_i + 1, best_j, best_j + 1

        # 3. Yield the refined opcodes for the block *after* the synch point
        yield from self._refine_replace_block(best_i + 1, i2, best_j + 1, j2)


def _get_intra_line_opcodes(from_line, to_line):
    if from_line is None or to_line is None:
        return []

    s = SequenceMatcher(None, from_line, to_line)
    return [(tag, i1, i2, j1, j2) for tag, i1, i2, j1, j2 in s.get_opcodes() if tag != EQUAL]


def mdiff(fromlines, tolines):
    """
    A simple generator that yields side-by-side diffs.
    It leverages the built-in refinement of the enhanced SequenceMatcher.

    Yields: (from_line, to_line, changed_flag)
    """
    s = SequenceMatcher(a=fromlines, b=tolines)

    for tag, i1, i2, j1, j2 in s.generate_opcodes(refine=True):
        if tag == EQUAL:
            for from_line in fromlines[i1:i2]:
                yield (from_line, from_line, False)

        elif tag == DELETE:
            for from_line in fromlines[i1:i2]:
                yield (from_line, None, True)

        elif tag == INSERT:
            for to_line in tolines[j1:j2]:
                yield (None, to_line, True)

        elif tag == REPLACE:
            from_chunk = fromlines[i1:i2]
            to_chunk = tolines[j1:j2]
            for i in range(max(len(from_chunk), len(to_chunk))):
                from_line = from_chunk[i] if i < len(from_chunk) else None
                to_line = to_chunk[i] if i < len(to_chunk) else None
                yield (from_line, to_line, True)
