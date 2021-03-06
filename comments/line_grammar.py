"""Grammar for line comments."""

import re
import textwrap

from ..dependencies.pypeg2 import (
    Concat,
    List,
    attr,
    contiguous,
    maybe_some,
    omit,
    some
)

Indentation = re.compile(r"[ \t]*")
Punctuation = re.compile(r"//+|#+")
Contents = re.compile(r".+")


class Prefix(Concat):
    grammar = (Indentation,
               attr("punctuation", Punctuation),
               re.compile(r"( |(?=\w)|(?=\n)|$)"))


class Line(Concat):
    grammar = attr("prefix", Prefix), attr("contents", Contents), "\n"


class SeparatorLine(Concat):
    grammar = Prefix, "\n"


class Separator(List):
    grammar = SeparatorLine, omit(maybe_some(SeparatorLine))


class ContiguousParagraph(List):
    def compose(self, parser, attr_of=None):
        # find the original line prefix and its length in characters
        prefix = parser.compose(self[0].prefix)
        prefix_length = len(prefix.expandtabs(parser.tab_size))

        # add the contents of all lines together
        contents = " ".join([l.contents.strip() for l in self if l.contents])

        # wrap the text at the remaining width
        width = parser.width - prefix_length
        lines = textwrap.wrap(contents, width, break_on_hyphens=False)

        # prepend the prefix to all lines
        for i in range(0, len(lines)):
            lines[i] = prefix + lines[i] + "\n"

        return "".join(lines)


class Paragraph(ContiguousParagraph):
    grammar = some(Line)


class Paragraphs(List):
    grammar = Paragraph, maybe_some([Separator, Paragraph])


class LineComment:
    grammar = contiguous(attr("paragraphs", Paragraphs))
