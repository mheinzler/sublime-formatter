"""Format different kinds of structured text."""

import sublime
import sublime_plugin

from . import comments

original_rulers = None


def debug():
    """Determine whether to we are in debugging mode."""

    # look through all open files to see if this plugin is currently being
    # edited
    for w in sublime.windows():
        for v in w.views():
            if v.file_name() == __file__:
                return True

    return False


def reload_modules():
    """Reload all modules that belong to this plugin."""
    import sys
    import imp

    # XXX: do this twice to make sure they are reloaded correctly
    for i in range(2):
        for m in sys.modules.keys():
            if m.startswith("sublime-formatter.") and "dependencies" not in m:
                imp.reload(sys.modules[m])


class FormatterCommand(sublime_plugin.TextCommand):
    """Sublime Text command for formatting structured text."""

    def run(self, edit, command):
        """Run the command."""
        self.edit = edit

        # reload modules if we are currently debugging
        if debug():
            reload_modules()

        if command == "apply_rulers":
            self.apply_rulers()
        elif command == "restore_rulers":
            self.apply_rulers(restore=True)
        elif command == "format":
            self.format()

    def apply_rulers(self, restore=False):
        """
        Apply or restore the current view's rulers globally.

        This can be used to trick DoxyDoxygen into using the view's rulers as
        the preferred line width.
        """

        global original_rulers

        preferences = sublime.load_settings('Preferences.sublime-settings')
        if not restore:
            original_rulers = preferences.get("rulers")
            preferences.set("rulers", self.view.settings().get("rulers"))
        else:
            preferences.set("rulers", original_rulers)
            original_rulers = None

    def format(self):
        """Format the text at the current selection."""

        # run a formatter based on the current selection
        for s in self.view.sel():
            position = s.b
            if self.view.match_selector(position,
                                        "comment.line"):
                comments.FormatLineComment(self.view, self.edit,
                                           position)
            elif self.view.match_selector(position,
                                          "source.c++ comment.block.c"):
                comments.FormatDoxygenCppBlockComment(self.view, self.edit,
                                                      position)
