"""Format Doxygen C++ block comments."""

import re

from .cpp_block_grammar import BlockComment
from ..dependencies.pypeg2 import Parser


def FormatDoxygenCppBlockComment(view, edit, pos):
    """Format a Doxygen C++ block comment."""
    if not view.match_selector(pos, "source.c++ comment.block.c"):
        return

    # extract the comment from the view
    scope = view.full_line(view.extract_scope(pos))
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
    t, c = parser.parse(comment, BlockComment)
    if t:
        raise parser.last_error

    # format the comment nicely
    formatted_comment = parser.compose(c)

    # update the view
    if formatted_comment != comment:
        view.replace(edit, scope, formatted_comment)
