#!/usr/bin/env python3

import argparse
import os
import re
import subprocess
import sys

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu


def exec_action(action):
    subprocess.run(action.data(), shell=True)


class MenuDescriptionParser:
    text_entry_regex = re.compile(r"- (?:\[(?P<checkbox> |x)\] )?(?P<title>.*)")
    command_regex = re.compile(r"\s+(?P<command>.+)")
    separator_regex = re.compile(r"---+(?:\s+(?P<section>.+))?")

    def __init__(self, menu):
        self.menu = menu
        self.current_action = None

    def parse(self, text):
        lines = text.strip().split("\n")
        self.parse_entry(lines)

    def parse_entry(self, lines):
        if not lines:
            return

        line, *lines = lines

        m = self.text_entry_regex.fullmatch(line)
        if m:
            self.current_action = self.menu.addAction(m["title"])

            self.current_action.triggered.connect(
                lambda _, action=self.current_action: exec_action(action)
            )

            if m["checkbox"]:
                self.current_action.setCheckable(True)
                if m["checkbox"] == "x":
                    self.current_action.setChecked(True)

            return self.parse_cmd_or_entry(lines)

        m = self.separator_regex.fullmatch(line)
        if m:
            self.current_action = None
            if m["section"]:
                self.menu.addSection(m["section"])
            else:
                self.menu.addSeparator()

            return self.parse_entry(lines)

        raise ValueError(f"unexpected input {line!r}")

    def parse_cmd_or_entry(self, lines):
        if not lines:
            return

        m = self.command_regex.fullmatch(lines[0])
        if m:
            assert self.current_action is not None
            self.current_action.setData(m["command"])
            return self.parse_entry(lines[1:])

        if self.current_action:
            self.current_action.setEnabled(False)
        self.parse_entry(lines)


def set_menu(reason):
    global menu

    if args.command:
        menu_description = subprocess.check_output(args.other, encoding="utf-8")
    else:
        with open(args.other[0]) as fp:
            menu_description = fp.read()

    menu = QMenu()
    MenuDescriptionParser(menu).parse(menu_description)

    menu.addAction("Quit").triggered.connect(app.exit)

    tray.setContextMenu(menu)
    menu.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    argparser = argparse.ArgumentParser()
    argparser.add_argument("--icon", default="mail-forward")
    argparser.add_argument("--title", default="Command Tray")
    argparser.add_argument("--command", action="store_true")
    argparser.add_argument("other", nargs="+")
    args = argparser.parse_args(app.arguments()[1:])

    if not args.command and len(args.other) > 1:
        argparser.error("only 1 file should be given")

    xdg_path = os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share"
    QIcon.setThemeSearchPaths(
        f"{data_dir}/icons"
        for data_dir in xdg_path.split(":")
    )
    icon = QIcon.fromTheme(args.icon)
    if icon.isNull():
        icon = QIcon(args.icon)

    app.setWindowIcon(icon)
    app.setApplicationDisplayName(args.title)

    tray = QSystemTrayIcon(icon)
    tray.setToolTip(args.title)
    tray.activated.connect(set_menu)

    menu = QMenu()
    tray.setContextMenu(menu)

    tray.show()
    app.exec()
