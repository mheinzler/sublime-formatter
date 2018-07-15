"""Grammar for paragraphs."""

from textwrap import TextWrapper, wrap
import re

from ..dependencies.pypeg2 import *


Indentation = re.compile(r"[ \t]*")
Contents = re.compile(r"[^\+\-\*].+")


class Line(Concat):
    grammar = (attr("indentation", Indentation),
               attr("contents", Contents), "\n")


class Text(List):
    grammar = some(Line)

    def compose(self, parser, attr_of=None):
        # find the original line indentation and its length in characters
        indentation = self[0].indentation
        indentation_length = len(indentation.expandtabs(parser.tab_size))

        # add the contents of all lines together
        contents = " ".join([l.contents.strip() for l in self if l.contents])

        # wrap the text at the remaining width
        width = parser.width - indentation_length
        lines = wrap(contents, width)

        # prepend the indentation to all lines
        for i in range(0, len(lines)):
            lines[i] = indentation + lines[i] + "\n"

        return "".join(lines)


ListItemStart = re.compile(r"[\+\-\*] ")


class ListItemStartLine(Concat):
    grammar = (attr("indentation", Indentation),
               attr("start", ListItemStart),
               attr("contents", Contents), "\n")


class ListItemLine(Concat):
    grammar = (attr("indentation", Indentation),
               attr("contents", Contents), "\n")


class ListItem(List):
    grammar = ListItemStartLine, maybe_some(ListItemLine)

    def compose(self, parser, attr_of=None):
        # find the original line indentation and its length in characters
        indentation = self[0].indentation
        indentation_length = len(indentation.expandtabs(parser.tab_size))

        # add the contents of all lines together
        contents = " ".join([l.contents.strip() for l in self if l.contents])

        # wrap the text at the remaining width
        width = parser.width - indentation_length
        wrapper = TextWrapper(width=width, initial_indent=self[0].start)

        # indent all but the first lines with an additional level
        wrapper.subsequent_indent = " " * parser.tab_size

        lines = wrapper.wrap(contents)

        # prepend the indentation to all lines
        for i in range(0, len(lines)):
            # turn the subsequent indentation into a tab character
            if i > 0:
                lines[i] = re.sub(r"^" + wrapper.subsequent_indent, "\t",
                                  lines[i])

            lines[i] = indentation + lines[i] + "\n"

        return "".join(lines)


class ListItems(List):
    grammar = some(ListItem)


class Paragraph:
    grammar = attr("paragraph", some([ListItems, Text]))
