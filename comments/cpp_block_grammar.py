"""Grammar for Doxygen C++ block comments."""

import re
import textwrap

from ..dependencies.pypeg2 import (
    Concat,
    List,
    Symbol,
    attr,
    blank,
    contiguous,
    ignore,
    maybe_some,
    omit,
    optional,
    some
)


def to_class_name(s):
    # remove invalid characters
    s = re.sub('[^0-9a-zA-Z_]', '', s)

    # remove leading characters until we find a letter or underscore
    s = re.sub('^[^a-zA-Z_]+', '', s)

    return s.title()


Indentation = re.compile(r"\t*")
Contents = re.compile(r".*")


# This must be a Symbol to be able to compose expressions like "<unnamed>". Not
# sure what the problem with this is.
class Expression(Symbol):
    regex = re.compile(r"\S+")


commands = ["@brief", "@tparam", "@param", "@return",
            "@code", "@endcode", "@note", "@warning", "@throws", "@see",
            "@related", "@relatedalso",
            r"\|", r"\[.+\]:", r"[\+\-\*]"]
CommandContents = re.compile(r"(?!\t*(?:" + r"|".join(commands) + r")).+")


class Start(Concat):
    grammar = Indentation, re.compile(r"/\*\*|/\*"), "\n"


class Prefix(Concat):
    grammar = Indentation, re.compile(r" \*(\t+|(?=\n)|$)")


class PrefixFixed(Concat):
    grammar = Indentation, re.compile(r" \*(\t|(?=\n)|$)")


class End(Concat):
    grammar = Indentation, re.compile(r"\*\*/| \*/"), "\n"


def HeaderLine(command, *parameters, main_command=None):
    grammar = (attr("prefix", Prefix), command, omit(re.compile(r"[ \t]*")),
               attr("parameters", parameters),
               attr("contents", optional(Contents)), "\n")

    # create a new class for this command with the above grammar
    class_name = to_class_name(main_command or command) + "HeaderLine"
    grammar_class = type(class_name, (Concat,), {
        "grammar": grammar
    })

    return grammar_class


class Line(Concat):
    grammar = attr("prefix", Prefix), attr("contents", Contents), "\n"


class SeparatorLine(Concat):
    grammar = Prefix, "\n"


class CommandLine(Concat):
    grammar = attr("prefix", Prefix), attr("contents", CommandContents), "\n"


class Separator(List):
    grammar = SeparatorLine, omit(maybe_some(SeparatorLine))


class ContiguousParagraph(List):
    def compose(self, parser, attr_of=None):
        # find the original line prefix and its length in characters
        prefix = parser.compose(self[0].prefix)
        prefix_length = len(prefix.expandtabs(parser.tab_size))

        # construct the header string if any
        header = self.command
        if header:
            header += " "

        # if a specific indentation was requested we need to adjust the header
        parameter_indentation = getattr(self, "parameter_indentation", 0)
        if parameter_indentation > len(header):
            header += " " * (parameter_indentation - len(header))

        if getattr(self[0], "parameters", None):
            header += parser.compose(self[0].parameters) + " "

        # align the content
        content_indentation = getattr(self, "content_indentation", 0)
        if content_indentation > len(header):
            header += " " * (content_indentation - len(header))

        header_length = len(header)

        # add the contents of all lines together
        contents = " ".join([l.contents.strip() for l in self if l.contents])

        # wrap the text at the remaining width after indentation
        indentation_length = prefix_length + header_length
        width = parser.width - indentation_length

        lines = textwrap.wrap(contents, width, break_on_hyphens=False)

        # construct the header line
        lines[0] = prefix + header + lines[0] + "\n"

        # calculate the required indentation in tabs and spaces
        indentation_tabs = (int(indentation_length / parser.tab_size)
                            - int(prefix_length / parser.tab_size))
        indentation_spaces = indentation_length % parser.tab_size
        indentation = "\t" * indentation_tabs + " " * indentation_spaces

        # prepend the prefix and indentation to all other lines
        for i in range(1, len(lines)):
            lines[i] = prefix + indentation + lines[i] + "\n"

        return "".join(lines)


class BreakingParagraph(List):
    def compose(self, parser, attr_of=None):
        indentation = "\t"

        # find the original line prefix
        prefix = parser.compose(self[0].prefix)

        # add the contents of all lines together
        contents = " ".join([l.contents.strip() for l in self if l.contents])

        # wrap the text at the remaining width after indentation
        indentation_length = len((prefix + indentation)
                                 .expandtabs(parser.tab_size))
        width = parser.width - indentation_length

        lines = textwrap.wrap(contents, width, break_on_hyphens=False)

        # construct the header line
        header = self.command
        if self[0].parameters:
            header += " " + parser.compose(self[0].parameters)

        lines.insert(0, prefix + header + "\n")

        # prepend the prefix and indentation to all other lines
        for i in range(1, len(lines)):
            lines[i] = prefix + indentation + lines[i] + "\n"

        return "".join(lines)


class Brief(ContiguousParagraph):
    command = "@brief"
    grammar = HeaderLine(command), maybe_some(CommandLine)


class Details(ContiguousParagraph):
    command = ""
    grammar = some(CommandLine)


# remove <unnamed> parameters as they are not needed and most likely were
# incorrectly generated by DoxyDoxygen
class UnnamedParam(ContiguousParagraph):
    command = "@param"
    grammar = HeaderLine(command, "<unnamed>"), maybe_some(CommandLine)


class TParam(ContiguousParagraph):
    command = "@tparam"
    grammar = HeaderLine(command, Expression), maybe_some(CommandLine)


class Param(ContiguousParagraph):
    command = "@param"
    grammar = HeaderLine(command, Expression), maybe_some(CommandLine)


Parameter = [
    ignore(UnnamedParam),
    TParam,
    Param
]


class Parameters(List):
    grammar = (some(Parameter),
               maybe_some(omit(Separator), some(Parameter)))

    def compose(self, parser, attr_of=None):
        # find the common indentation level of all parameters
        parameter_indentation = max(map(
            lambda p: len(p.command) + 1, self))
        content_indentation = parameter_indentation + max(map(
            lambda p: len(p[0].parameters) + 1, self))

        # tell the parameter paragraphs of the correct indentation
        for p in self:
            p.parameter_indentation = parameter_indentation
            p.content_indentation = content_indentation

        # compose all parameter paragraphs together
        return "".join(map(lambda p: parser.compose(p), self))


class Returns(ContiguousParagraph):
    command = "@returns"
    grammar = (HeaderLine([command, "@return"], main_command=command),
               maybe_some(CommandLine))


class ParametersReturns(Concat):
    # grammar = Parameters, optional(omit(optional(Separator)), Returns)
    grammar = Parameters, omit(optional(Separator)), Returns


class CodeLine(Concat):
    grammar = (attr("prefix", PrefixFixed),
               attr("contents", re.compile(r"(?!\t*@endcode).+")),
               "\n")


class EndCodeLine(Concat):
    grammar = attr("prefix", Prefix), "@endcode", "\n"


class Code(BreakingParagraph):
    command = "@code"
    grammar = (HeaderLine(command, optional(re.compile(r"\{.+?\}"))),
               maybe_some([CodeLine, Separator]),
               EndCodeLine)

    def compose(self, parser, attr_of=None):
        indentation = "\t"

        # find the original line prefix
        prefix = parser.compose(self[0].prefix)

        # add the contents of all but the first and last lines together
        contents = ""
        for i in range(1, len(self) - 1):
            line = self[i]
            if hasattr(line, "contents"):
                contents += line.contents

            contents += "\n"

        # remove any common indentation
        lines = textwrap.dedent(contents).splitlines()

        # add the @code line
        header = self.command
        if self[0].parameters:
            header += self[0].parameters

        lines.insert(0, prefix + header + "\n")

        # prepend the prefix and indentation to all code lines
        for i in range(1, len(lines)):
            lines[i] = (prefix + indentation + lines[i]).rstrip() + "\n"

        # add the @endcode line
        lines.append(parser.compose(self[-1]))

        return "".join(lines)


class Note(BreakingParagraph):
    command = "@note"
    grammar = HeaderLine(command), maybe_some(CommandLine)


class Warning(BreakingParagraph):
    command = "@warning"
    grammar = HeaderLine(command), maybe_some(CommandLine)


class Throws(BreakingParagraph):
    command = "@throws"
    grammar = HeaderLine(command, Expression), maybe_some(CommandLine)


See = HeaderLine("@see", blank)


Related = HeaderLine("@related", blank)


RelatedAlso = HeaderLine("@relatedalso", blank)


class TableRow(Concat):
    grammar = attr("prefix", Prefix), "|", attr("contents", Contents), "\n"


class Table(List):
    grammar = some(TableRow)


ListItemStart = re.compile(r"[\+\-\*] ")


class ListItemStartLine(Concat):
    grammar = (attr("prefix", PrefixFixed),
               attr("indentation", Indentation),
               attr("start", ListItemStart),
               attr("contents", Contents), "\n")


class ListItemLine(Concat):
    grammar = (attr("prefix", Prefix),
               attr("contents", re.compile(r"[^\+\-\*\n].*")), "\n")


class ListItem(List):
    grammar = ListItemStartLine, maybe_some(ListItemLine)

    def compose(self, parser, attr_of=None):
        # find the original line prefix and indentation
        prefix = parser.compose(self[0].prefix)
        indentation = self[0].indentation

        # add the contents of all lines together
        contents = " ".join([l.contents.strip() for l in self if l.contents])

        # wrap the text at the remaining width
        indentation_length = len((prefix + indentation)
                                 .expandtabs(parser.tab_size))
        width = parser.width - indentation_length

        wrapper = textwrap.TextWrapper(width=width,
                                       initial_indent=self[0].start,
                                       break_long_words=False,
                                       break_on_hyphens=False)

        # indent all but the first lines with an additional level
        wrapper.subsequent_indent = " " * parser.tab_size

        lines = wrapper.wrap(contents)

        # prepend the prefix and indentation to all lines
        for i in range(0, len(lines)):
            # turn the subsequent indentation into a tab character
            if i > 0:
                lines[i] = re.sub(r"^" + wrapper.subsequent_indent, "\t",
                                  lines[i])

            lines[i] = prefix + indentation + lines[i] + "\n"

        return "".join(lines)


class BreakingListItemStartLine(Concat):
    grammar = (attr("prefix", PrefixFixed),
               attr("indentation", Indentation),
               attr("start", ListItemStart),
               attr("contents", re.compile(r".*<br>")), "\n")


class BreakingListItem(BreakingParagraph):
    grammar = BreakingListItemStartLine, maybe_some(ListItemLine)

    def compose(self, parser, attr_of=None):
        # find the original line prefix and indentation
        prefix = parser.compose(self[0].prefix)
        indentation = self[0].indentation + "\t"

        # add the contents of all lines together
        contents = " ".join([l.contents.strip() for l in self[1:]
                             if l.contents])

        # wrap the text at the remaining width
        indentation_length = len((prefix + indentation)
                                 .expandtabs(parser.tab_size))
        width = parser.width - indentation_length

        wrapper = textwrap.TextWrapper(width=width,
                                       break_long_words=False,
                                       break_on_hyphens=False)

        lines = wrapper.wrap(contents)

        # construct the start line
        start = parser.compose(self[0])
        lines.insert(0, start)

        # prepend the prefix and indentation to all other lines
        for i in range(1, len(lines)):
            lines[i] = prefix + indentation + lines[i] + "\n"

        return "".join(lines)


class ListItems(List):
    grammar = some([BreakingListItem, ListItem])


class ReferenceLink(Concat):
    grammar = Prefix, re.compile(r"\[.+\]: .*"), "\n"


Paragraph = [
    Brief,
    ParametersReturns,
    Parameters,
    Returns,
    Code,
    Note,
    Warning,
    Throws,
    See,
    RelatedAlso,
    Related,
    Table,
    ListItems,
    ReferenceLink,
    Details
]


class Paragraphs(List):
    grammar = Paragraph, maybe_some([Separator, Paragraph])


class BlockComment:
    grammar = contiguous(attr("start", Start),
                         attr("paragraphs", Paragraphs),
                         attr("end", End))
