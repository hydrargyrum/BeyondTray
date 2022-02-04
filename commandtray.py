#!/usr/bin/env python3

import argparse
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
        for regex, converter in desc_parsing.items():
            m = regex.fullmatch(line)
            if m:
                converter(res, m)
                break
    return res


def set_menu(reason):
    global menu

    #if reason != QSystemTrayIcon.Context:
    #	return

    menu_description = subprocess.check_output(sys.argv[1:], encoding="utf-8")
    menu = parse_menu(menu_description)

    #menu = QMenu()
    #menu.addAction("lol")
    menu.addAction("Quit").triggered.connect(app.exit)

    tray.setContextMenu(menu)
    menu.show()


app = QApplication(sys.argv)

QIcon.setThemeSearchPaths(
    f"{data_dir}/icons"
    for data_dir in "/usr/local/share/:/usr/share/".split(":")
)
tray = QSystemTrayIcon(QIcon.fromTheme("mail-forward"))

tray.activated.connect(set_menu)

menu = QMenu()
tray.setContextMenu(menu)

tray.show()
app.exec()
