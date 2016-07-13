#!/usr/bin/env bash

for f in Lib/glyphsLib/*_test.py; do
    echo "$(basename "$f")"
    python "$f"
    if [[ "$?" -ne 0 ]]; then
        exit 1
    fi
done
