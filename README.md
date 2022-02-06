
```
commandtray COMMAND [ARGS...]
```

`commandtray` shows a system tray icon with a dynamic, customizable menu.
Given this input
```
- The &first menu entry
    xmessage "the first entry was selected"
- &Another entry
    echo "the second entry was selected" >> ~/foobar.txt
- This is a disabled entry (no command associated)
--------
- The above dashes are a separator
- [ ] This is a &checkable entry
    echo "the checkbox was checked" >> ~/foobar.txt
- [ ] This is a checkable entry (but it's disabled)
- [x] This is a checked &entry
    echo "the checkbox was unchecked" >> ~/foobar.txt
--------
> A &sub-menu
    - an entry in the sub-menu
        xmessage "submenu was selected"
-------- This is a separator with a title
- A last entry that opens &Gitlab.com
    firefox https://gitlab.com
```

commandtray will show this menu:

![]()

The menu is dynamic because a command can be used to generate the input file just when the menu is about to be shown.

At start, commandtray shows an icon that rests in the system tray.
When the user right-clicks on it (or requests the context menu in any way), `commandtray` runs COMMAND with arguments ARGS which should output a menu description to stdout.
`commandtray` displays a menu corresponding to that description.
When selected, a menu entry runs a command, as configured in the menu description.

