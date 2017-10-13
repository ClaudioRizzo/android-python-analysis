#!/bin/bash

# Vulnerable is the list of all the apk sha256 found vulnerable
# logs is the folder with all the logs of the stimulation + injection

for i in $(cat vulnerables.txt); do
	if grep -q -E ".*INFO:CONSOLE.*BabelView.*\"" results/"$i".logcat; then
		echo "$i"
	fi
done
