import difflib
from enum import Enum


class Tag(Enum):
    REPLACE = 0
    DELETE  = 1
    INSERT  = 2
    EQUAL   = 3
    COUNT   = 4


REPLACE = Tag.REPLACE 
DELETE  = Tag.DELETE  
INSERT  = Tag.INSERT  
EQUAL   = Tag.EQUAL   
COUNT   = Tag.COUNT   


class SequenceMatcher(difflib.SequenceMatcher):
    def get_opcodes(self):
        """Same as difflib.SequenceMatcher.get_opcodes just uses int tag instead of str"""
        if self.opcodes is not None:
            return self.opcodes
        i = j = 0
        self.opcodes = answer = []
        for ai, bj, size in self.get_matching_blocks():
            tag = COUNT
            if i < ai and j < bj:
                tag = REPLACE
            elif i < ai:
                tag = DELETE
            elif j < bj:
                tag = INSERT
            if tag != COUNT:
                answer.append( (tag, i, ai, j, bj) )
            i, j = ai+size, bj+size
            if size:
                answer.append( (EQUAL, ai, i, bj, j) )
        return answer


def _get_intra_line_opcodes(from_line, to_line):
    if from_line is None or to_line is None:
        return []
        
    s = SequenceMatcher(None, from_line, to_line)
    return [(tag, i1, i2, j1, j2) for tag, i1, i2, j1, j2 in s.get_opcodes() if tag != EQUAL]


def fancy_replace(from_chunk, to_chunk):
    """
    A generator that mimics difflib.Differ._fancy_replace.
    It finds the best matching "synch" line in a replaced block and yields
    diffs recursively.
    """
    cruncher = SequenceMatcher()
    
    # Base cases for recursion
    if not from_chunk:
        for line in to_chunk:
            yield (None, line, True, False)
        return
    if not to_chunk:
        for line in from_chunk:
            yield (line, None, True, False)
        return

    # Find the best matching pair of lines in the chunks
    best_ratio, cutoff = 0.49, 0.50
    best_i, best_j = None, None

    for j, to_line in enumerate(to_chunk):
        cruncher.set_seq2(to_line)
        for i, from_line in enumerate(from_chunk):
            cruncher.set_seq1(from_line)
            if (
                cruncher.real_quick_ratio() > best_ratio and
                cruncher.quick_ratio() > best_ratio and
                cruncher.ratio() > best_ratio
            ):
                best_ratio, best_i, best_j = cruncher.ratio(), i, j

    if best_ratio < cutoff:
        # No good match found, treat as a plain replace.
        for i in range(max(len(from_chunk), len(to_chunk))):
            from_line = from_chunk[i] if i < len(from_chunk) else None
            to_line = to_chunk[i] if i < len(to_chunk) else None
            yield (from_line, to_line, True, False)
        return

    # A good match was found, use it as a synch point and recurse
    # 1. Yield diffs for the part *before* the synch point
    yield from fancy_replace(from_chunk[:best_i], to_chunk[:best_j])

    # 2. Yield the synch point itself
    from_line, to_line = from_chunk[best_i], to_chunk[best_j]
    yield (from_line, to_line, True, True)

    # 3. Yield diffs for the part *after* the synch point
    yield from fancy_replace(from_chunk[best_i+1:], to_chunk[best_j+1:])


def mdiff(fromlines, tolines):
    """
    A generator that yields side-by-side diffs.

    Yields: (from_line, to_line, changed_flag, similar_flag)
    """
    s = SequenceMatcher(None, fromlines, tolines)
    for tag, i1, i2, j1, j2 in s.get_opcodes():
        if tag == EQUAL:
            for from_line in fromlines[i1:i2]:
                yield (from_line, from_line, False, False)
        
        elif tag == DELETE:
            for from_line in fromlines[i1:i2]:
                yield (from_line, None, True, False)
        
        elif tag == INSERT:
            for to_line in tolines[j1:j2]:
                yield (None, to_line, True, False)
        
        elif tag == REPLACE:
            from_chunk = fromlines[i1:i2]
            to_chunk = tolines[j1:j2]
            yield from fancy_replace(from_chunk, to_chunk)


