"""Format line comments."""

import re

import sublime

from .line_grammar import LineComment
from ..dependencies.pypeg2 import Parser


def is_valid_line_comment(view, region):
    """Check if region contains a line comment."""

    # the region must end in a line comment
    if (region.empty()
            or not view.match_selector(region.end() - 1, "comment.line")):
        return False

    # now check if everything before the comment consists only of spaces and
    # tabs (only check this if the comment starts within the region)
    scope = view.extract_scope(region.end())
    if region.begin() < scope.begin():
        indentation = view.substr(sublime.Region(region.begin(),
                                                 scope.begin()))
        if indentation and not indentation.isspace():
            return False

    return True


def extract_line_comment_scope(view, pos):
    """Return the scope of adjacent line comments."""

    # find the current and the last row
    row = view.rowcol(pos)[0]
    max_rows = view.rowcol(view.size())[0]

    # find the start of the comments by checking the lines above
    begin = -1
    for l in range(row, -1, -1):
        line = view.line(view.text_point(l, 0))
        if not is_valid_line_comment(view, line):
            break

        begin = line.begin()

    if begin == -1:
        # the comment at pos is invalid
        return None

    # find the end of the comments by checking the lines below
    end = pos
    for l in range(row + 1, max_rows + 1):
        line = view.line(view.text_point(l, 0))
        if not is_valid_line_comment(view, line):
            break

        end = line.end()

    # return the region for all comment lines
    return view.full_line(sublime.Region(begin, end))


def FormatLineComment(view, edit, pos):
    """Format a line comment."""
    if not view.match_selector(pos, "comment.line"):
        return

    # extract the comment from the view
    scope = extract_line_comment_scope(view, pos)
    if not scope:
        return

    comment = view.substr(scope)

    # initialize the parser
    parser = Parser()
    parser.text = comment
    parser.whitespace = re.compile(r"\0")  # disable automatic removal
    parser.autoblank = False

    # custom parameters for the compose methods
    rulers = view.settings().get("rulers", [])

    parser.width = (rulers and rulers[0]) or 80
    parser.tab_size = view.settings().get("tab_size")

    # try to parse the original comment
    t, c = parser.parse(comment, LineComment)
    if t:
        raise parser.last_error

    # format the comment nicely
    formatted_comment = parser.compose(c)

    # update the view
    if formatted_comment != comment:
        view.replace(edit, scope, formatted_comment)
