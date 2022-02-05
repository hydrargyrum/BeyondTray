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


def parse_separator(menu, _):
    menu.addSeparator()


def parse_section(menu, match):
    menu.addSection(match[1])


def parse_disabled(menu, match):
    action = menu.addAction(match[1])
    action.setEnabled(False)


def parse_cmd(menu, match):
    action = menu.addAction(match[1])
    action.setData(match[2])
    action.triggered.connect(lambda _, action=action: exec_action(action))


def parse_checkbox(menu, match, disabled=False):
    action = menu.addAction(match[2])
    if disabled:
        action.setEnabled(False)
    else:
        action.setData(match[3])
    action.setCheckable(True)
    action.setChecked(match[1] == "x")
    action.triggered.connect(lambda _, action=action: exec_action(action))


def parse_disabled_checkbox(menu, match):
    parse_checkbox(menu, match, disabled=True)


desc_parsing = {
    re.compile("---+"): parse_separator,
    re.compile("---+ (.*)"): parse_section,
    re.compile(r"\[( |x)\] (.*)\t(.*)"): parse_checkbox,
    re.compile(r"\[( |x)\] (.*)"): parse_disabled_checkbox,
    re.compile(r"(.*)\t(.*)"): parse_cmd,
    re.compile(r"(.*)"): parse_disabled,
}


def parse_menu(text):
    res = QMenu()
    lines = text.strip().split("\n")

    for line in lines:
        if not line:
            continue

        for regex, converter in desc_parsing.items():
            m = regex.fullmatch(line)
            if m:
                converter(res, m)
                break
    return res


def set_menu(reason):
    global menu

    if args.command:
        menu_description = subprocess.check_output(args.other, encoding="utf-8")
    else:
        with open(args.other[0]) as fp:
            menu_description = fp.read()

    menu = parse_menu(menu_description)

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
