#!/bin/bash
if [ "$1" == "gpt5" ]; then
    cp .claude/settings.gpt5.json .claude/settings.json
    echo "Now using GPT-5"
elif [ "$1" == "stock" ]; then
    git checkout .claude/settings.json
    echo "Reverted to stock"
else
    echo "Usage: $0 [gpt5|stock]"
fi
