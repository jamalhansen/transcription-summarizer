#!/bin/zsh
# Voice journal runner — edit the variables below to change behavior

PROVIDER="ollama"
MODEL="phi4"

# Uncomment and set these if needed:
# EXTRA_ARGS="--some-flag"

INPUT_DIR="${HOME}/Library/Mobile Documents/com~apple~CloudDocs/Documents/Voice"

cd "$(dirname "$0")"
brctl download "${INPUT_DIR}" 2>/dev/null
sleep 5
uv run voice_journal.py --provider "$PROVIDER" --model "$MODEL" ${EXTRA_ARGS:-}
