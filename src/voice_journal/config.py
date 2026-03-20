import os
from pathlib import Path

DEFAULT_INPUT_DIR = "~/Library/Mobile Documents/com~apple~CloudDocs/Documents/Voice/"
DEFAULT_VAULT_PATH = os.environ.get("OBSIDIAN_VAULT_PATH", "~/vaults/BrainSync/")
DEFAULT_NOTE_DIR = "Timeline"
DEFAULT_TEMPLATE_PATH = os.environ.get(
    "VOICE_JOURNAL_TEMPLATE",
    "~/vaults/BrainSync/Templates/Daily Note.md",
)


def resolve_input_dir(path: str | None) -> Path:
    return Path(path or DEFAULT_INPUT_DIR).expanduser()


def resolve_vault_path(path: str | None) -> Path:
    return Path(path or DEFAULT_VAULT_PATH).expanduser()
