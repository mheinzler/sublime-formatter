"""Format simple paragraphs."""

import re

import sublime

from .paragraph_grammar import Paragraph
from ..dependencies.pypeg2 import Parser


def extract_paragraph_scope(view, pos):
    """Return the scope of paragraph."""

    # find the current and the last row
    row = view.rowcol(pos)[0]
    max_rows = view.rowcol(view.size())[0]

    # find the start of the paragraph by searching for the first empty line
    # above
    begin = -1
    for l in range(row, -1, -1):
        line = view.line(view.text_point(l, 0))
        if line.empty():
            break

        begin = line.begin()

    if begin == -1:
        # there is on paragraph
        return None

    # find the end of the paragraph by checking the lines below
    end = pos
    for l in range(row + 1, max_rows + 1):
        line = view.line(view.text_point(l, 0))
        if line.empty():
            break

        end = line.end()

    # return the region for all lines
    return view.full_line(sublime.Region(begin, end))


def FormatParagraph(view, edit, pos):
    """Format a paragraph."""
    if not view.match_selector(pos, "text.plain, text.html.markdown"):
        return

    # extract the paragraph from the view
    scope = extract_paragraph_scope(view, pos)
    if not scope:
        return

    paragraph = view.substr(scope)

    # initialize the parser
    parser = Parser()
    parser.text = paragraph
    parser.whitespace = re.compile(r"\0")  # disable automatic removal
    parser.autoblank = False

    # custom parameters for the compose methods
    rulers = view.settings().get("rulers", [])

    parser.width = (rulers and rulers[0]) or 80
    parser.tab_size = view.settings().get("tab_size")

    # try to parse the original paragraph
    t, c = parser.parse(paragraph, Paragraph)
    if t:
        raise parser.last_error

    # format the paragraph nicely
    formatted_paragraph = parser.compose(c)

    # update the view
    if formatted_paragraph != paragraph:
        view.replace(edit, scope, formatted_paragraph)
