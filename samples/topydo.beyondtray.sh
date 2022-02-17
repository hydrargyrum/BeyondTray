#!/bin/sh -e
# usage: beyondtray --icon=/usr/share/icons/gnome-colors-common/32x32/apps/stock_todo.png --command topydo.beyondtray.sh

topydo ls | sed "s/^| \?\([0-9]*\)|/\1/" | while read id line
do
	echo "- [ ] ($id) $line"
	if echo "$line" | grep -q "(A)"
	then
		echo "    icon: /usr/share/icons/gnome/48x48/status/important.png"
	fi
	echo "    topydo do $id"
done
