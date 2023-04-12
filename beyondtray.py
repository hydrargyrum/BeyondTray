#!/usr/bin/env python3
# SPDX-License-Identifier: WTFPL

import argparse
import os
from pathlib import Path
import re
import subprocess
import sys

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu


def exec_action(action):
    subprocess.Popen(action.data(), shell=True)


ws_regex = re.compile(r"\s+")


class MenuDescriptionParser:
    text_entry_regex = re.compile(r"- (?:\[(?P<checkbox> |x)\] )?(?P<title>.*)")
    command_regex = re.compile(r"(?P<command>.+)")
    separator_regex = re.compile(r"---+(?:\s+(?P<section>.+))?")
    icon_regex = re.compile(r"icon: (?P<icon>\S+)")
    checked_regex = re.compile(r"\s+checked: (yes|no|true|false|1|0)")
    submenu_regex = re.compile(r"> (?P<title>.+)")

    automata = {
        "start": {
            text_entry_regex: "entry",
            separator_regex: "separator",
            submenu_regex: "submenu",
        },

        "entry": {
            text_entry_regex: "entry",
            separator_regex: "separator",
            submenu_regex: "submenu",
            icon_regex: "text_attrs",
            command_regex: "text_attrs",
        },
        "text_attrs": {
            text_entry_regex: "entry",
            separator_regex: "separator",
            submenu_regex: "submenu",
            icon_regex: "text_attrs",
            command_regex: "text_attrs",
        },

        "submenu": {
            icon_regex: "submenu_attrs",
            text_entry_regex: "entry",
            separator_regex: "separator",
            submenu_regex: "submenu",
        },
        "submenu_attrs": {
            text_entry_regex: "entry",
            separator_regex: "separator",
            submenu_regex: "submenu",
        },

        "separator": {
            text_entry_regex: "entry",
            separator_regex: "separator",
            submenu_regex: "submenu",
        },
    }

    def __init__(self, menu):
        self.menu_tree = [menu]
        self.current_action = None
        self.indent_width = 1
        self.lineno = 0

    def _get_indent(self, line):
        space_match = ws_regex.match(line)
        if space_match:
            return len(space_match[0])
        return 0

    def _error(self, message):
        raise SyntaxError(f"at line {self.lineno}: {message}")

    def parse(self, text):
        first_indent_match = re.search(r"^[ \t]+", text, flags=re.MULTILINE)
        if first_indent_match:
            self.indent_width = len(first_indent_match[0])

        lines = text.strip().split("\n")

        state = "start"
        for self.lineno, line in enumerate(lines, 1):
            if not line.strip():
                continue

            indent = self._get_indent(line)
            if indent and indent % self.indent_width != 0:
                self._error(f"indentation should be a multiple of {self.indent_width}")
            level = indent // self.indent_width

            line = line.strip()

            for regex, new_state in self.automata[state].items():
                m = regex.fullmatch(line)
                if m:
                    state = new_state
                    getattr(self, f"parse_{state}")(m, level)
                    break
            else:
                self._error(f"invalid line: {line}")

    def _check_attr_indent(self, level):
        if level != len(self.menu_tree):
            self._error("not indented properly")

    def _process_indent(self, level):
        # len([root]) = 1
        # indent("- foo") = 0
        # -> nothing to do

        # len([root, menu]) = 2
        # indent("- foo") = 0
        # -> drop `menu`

        # len([root, menu]) = 2
        # indent(" - foo") = 1
        # -> nothing to do

        level += 1
        max_depth = len(self.menu_tree)
        if level > max_depth:
            self._error("line is indented too much")
        elif level < max_depth:
            self.current_action = None
            del self.menu_tree[level:]

    def parse_entry(self, m, level):
        self._process_indent(level)

        self.current_action = self.menu_tree[-1].addAction(m["title"])
        self.current_action.setEnabled(False)

        self.current_action.triggered.connect(
            lambda _, action=self.current_action: exec_action(action)
        )

        if m["checkbox"]:
            self.current_action.setCheckable(True)
            if m["checkbox"] == "x":
                self.current_action.setChecked(True)

    def parse_separator(self, m, level):
        self._process_indent(level)

        self.current_action = None
        if m["section"]:
            self.menu_tree[-1].addSection(m["section"])
        else:
            self.menu_tree[-1].addSeparator()

    def parse_submenu(self, m, level):
        self._process_indent(level)

        self.current_action = None

        new = self.menu_tree[-1].addMenu(m["title"])
        self.menu_tree.append(new)

    def parse_text_attrs(self, m, level):
        self._check_attr_indent(level)

        if "command" in m.groupdict():
            if self.current_action is None:
                self._error(f"unexpected command after non-entry: {m['command']}")
            self.current_action.setEnabled(True)
            self.current_action.setData(m["command"])

        elif "icon" in m.groupdict():
            if self.current_action is None:
                self._error(f"unexpected icon after non-entry: {m['icon']}")
            self.current_action.setIcon(load_icon(m["icon"]))

        else:
            raise AssertionError()

    def parse_submenu_attrs(self, m, level):
        self._check_attr_indent(level)

        assert "icon" in m
        self.menu_tree[-1].setIcon(load_icon(m["icon"]))


def template_sh(command):
    # in shell 0 is success, so we map it to True
    return not subprocess.run(command, shell=True).returncode


def template_lines(command):
    return subprocess.run(
        command, shell=True, stdout=subprocess.PIPE, encoding="utf8",
    ).stdout.rstrip().split("\n")


def template_read(command):
    output = subprocess.run(
        command, shell=True, stdout=subprocess.PIPE, encoding="utf8",
    ).stdout

    # this function is to be called typically from menu entries titles,
    # not from commands to exec for a triggered entry.
    # so cleaning whitespace is preferable
    return ws_regex.sub(" ", output)


template_funcs = {
    "sh": template_sh,
    "read": template_read,
    "lines": template_lines,
    "getenv": os.getenv,
    "putenv": os.putenv,
}


def set_menu(reason):
    global menu

    if args.command:
        menu_description = subprocess.check_output(args.other, encoding="utf-8")
    else:
        with open(args.other[0]) as fp:
            menu_description = fp.read()

        if args.template:
            import jinja2

            template = jinja2.Template(menu_description)
            menu_description = template.render(**template_funcs)

    # XXX don't use menu.clear(). On some desktops like fluxbox, it seems the
    # menu "blinks" if the menu is empty at some point. So we remove old entries
    # when we added new ones.
    old_actions = menu.actions()

    try:
        MenuDescriptionParser(menu).parse(menu_description)
    except Exception as exc:
        print(f"error when parsing the menu: {exc}", file=sys.stderr)
        print(f"menu description:", file=sys.stderr)
        print(menu_description, file=sys.stderr)

        tray.showMessage(
            "BeyondTray cannot parse the menu", str(exc),
            QSystemTrayIcon.Critical,
        )

        menu.addSeparator()
        menu.addAction(f"BeyondTray cannot parse the menu: {exc}").setEnabled(0)

    menu.addSeparator()
    menu.addAction("Quit").triggered.connect(app.exit)

    for action in old_actions:
        menu.removeAction(action)
        action.deleteLater()


def load_icon(name):
    icon = QIcon.fromTheme(name)
    if icon.isNull():
        icon = QIcon(name)
    return icon


def main():
    global tray, app, args

    # avoid crashing the whole app on any exception
    if sys.excepthook is sys.__excepthook__:
        sys.excepthook = lambda *args: sys.__excepthook__(*args)

    app = QApplication(sys.argv)

    argparser = argparse.ArgumentParser()
    argparser.add_argument(
        "--icon", default=str(Path(__file__).with_name("hamburger-menu.png")),
    )
    argparser.add_argument("--title", default="BeyondTray")
    argparser.add_argument("--command", action="store_true")
    argparser.add_argument("--template", action="store_true")
    argparser.add_argument("other", nargs="+")
    args = argparser.parse_args(app.arguments()[1:])

    if not args.command and len(args.other) > 1:
        argparser.error("only 1 file should be given")

    if args.template:
        try:
            import jinja2
        except ImportError:
            parser.error("cannot use --template, jinja2 is not installed")

    xdg_path = os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share"
    QIcon.setThemeSearchPaths(
        f"{data_dir}/icons"
        for data_dir in xdg_path.split(":")
    )
    icon = load_icon(args.icon)

    app.setWindowIcon(icon)
    app.setApplicationDisplayName(args.title)
    app.setApplicationName("BeyondTray")

    tray = QSystemTrayIcon(icon)
    tray.setToolTip(args.title)
    tray.activated.connect(set_menu)

    menu = QMenu()
    # XXX this dummy entry is important!
    # On XFCE at least, if the context menu is empty when assigning it to tray,
    # right-clicking on the tray will spawn a desktop-environment menu, not ours
    # and neither QMenu.aboutToShow nor QSystemTrayIcon.activated will be
    # emitted, so we don't have a chance to populate our menu.
    # A dummy entry at least gives us the chance to be notified when we should.
    menu.addAction("dummy")
    tray.setContextMenu(menu)

    # the `activated` signal may not be emitted in case of context menu
    # aboutToShow seems more reliable.
    menu.aboutToShow.connect(lambda: set_menu(None))

    tray.show()
    app.exec()


if __name__ == "__main__":
    main()
