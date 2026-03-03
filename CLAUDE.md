Voice Memo Thought Extractor

## Project Overview

CLI tool that reads poorly transcribed voice memo files, interprets what the speaker actually meant, and extracts structured content into Obsidian daily notes. The core LLM challenge is semantic reconstruction of garbled transcription -- not grammar cleanup, but meaning recovery.

## What This Tool Does

1. Reads `.txt` transcription files from a configurable input directory (default: iCloud Documents/Voice)
2. Sends each transcription to an LLM with a system prompt that instructs it to interpret the intended meaning despite transcription errors
3. Extracts three categories from the corrected text:
   - **Thoughts** -- important ideas, reflections, observations
   - **Actions** -- things to do, follow-ups, commitments
   - **Gratitude** -- things the speaker is grateful for
4. Appends extracted content to (or creates) an Obsidian daily note in `YYYY-MM-DD.md` format

## Architecture

```
voice-journal/
  voice_journal.py        # CLI entrypoint (argparse)
  providers/
    __init__.py
    base.py               # Abstract provider interface
    local.py              # Ollama provider
    anthropic_provider.py # Anthropic API (Claude)
    groq_provider.py      # Groq API
    deepseek_provider.py  # DeepSeek API
  extractor.py            # Prompt construction + response parsing
  daily_note.py           # Obsidian daily note read/append/create logic
  config.py               # Defaults, env vars, path resolution
  tests/
    test_extractor.py
    test_daily_note.py
    test_providers.py
    fixtures/
      sample_garbled.txt  # Example poorly transcribed input
      sample_output.md    # Expected daily note output
```

## CLI Interface

```bash
# Basic usage -- process all voice files, write to daily note
python voice_journal.py

# Specify provider
python voice_journal.py --provider local          # Ollama (default)
python voice_journal.py --provider anthropic      # Claude via API
python voice_journal.py --provider groq           # Groq API
python voice_journal.py --provider deepseek       # DeepSeek API

# Dry run -- print extracted content to stdout, do not write to file
python voice_journal.py --dry-run
python voice_journal.py --provider anthropic --dry-run

# Custom paths
python voice_journal.py --input-dir ~/my-voice-memos/
python voice_journal.py --vault-path ~/vaults/BrainSync/ --note-dir Timeline

# Specify a single file
python voice_journal.py --file ~/Documents/Voice/memo-2026-03-03.txt

# Specify model (useful for local provider)
python voice_journal.py --provider local --model llama3.2:3b
python voice_journal.py --provider anthropic --model claude-haiku-4-5-20251001
```

## Arguments Reference

| Argument       | Short | Default                                                           | Description                                                      |
| -------------- | ----- | ----------------------------------------------------------------- | ---------------------------------------------------------------- |
| `--provider`   | `-p`  | `local`                                                           | LLM backend: local, anthropic, groq, deepseek                    |
| `--model`      | `-m`  | provider-specific                                                 | Override the default model for the chosen provider               |
| `--dry-run`    | `-n`  | false                                                             | Print output to stdout instead of writing to file                |
| `--input-dir`  | `-i`  | `~/Library/Mobile Documents/com~apple~CloudDocs/Documents/Voice/` | Directory containing voice transcription files                   |
| `--file`       | `-f`  | none                                                              | Process a single file instead of the whole directory             |
| `--vault-path` | `-v`  | env `OBSIDIAN_VAULT_PATH` or `~/vaults/BrainSync/`                | Path to the Obsidian vault root                                  |
| `--note-dir`   | `-d`  | `Timeline`                                                        | Subdirectory within vault for daily notes                        |
| `--date`       |       | today                                                             | Override the date for the daily note (YYYY-MM-DD)                |
| `--verbose`    |       | false                                                             | Print the raw transcription and corrected text before extraction |

## Environment Variables

| Variable              | Purpose                                      | Example                  |
| --------------------- | -------------------------------------------- | ------------------------ |
| `OBSIDIAN_VAULT_PATH` | Vault root path                              | `~/vaults/BrainSync/`    |
| `ANTHROPIC_API_KEY`   | Anthropic API key (for --provider anthropic) | `sk-ant-...`             |
| `GROQ_API_KEY`        | Groq API key (for --provider groq)           | `gsk_...`                |
| `DEEPSEEK_API_KEY`    | DeepSeek API key (for --provider deepseek)   | `sk-...`                 |
| `OLLAMA_HOST`         | Ollama server URL (for --provider local)     | `http://localhost:11434` |

## Provider Interface

Each provider implements this interface:

```python
class BaseProvider:
    def __init__(self, model: str | None = None):
        """Initialize with optional model override."""
        ...

    def complete(self, system_prompt: str, user_message: str) -> str:
        """Send a completion request and return the response text."""
        ...

    @property
    def default_model(self) -> str:
        """Return the default model name for this provider."""
        ...
```

Default models per provider:

- **local**: `llama3.2:3b` (via Ollama)
- **anthropic**: `claude-haiku-4-5-20251001`
- **groq**: `llama-3.3-70b-versatile`
- **deepseek**: `deepseek-chat`

## The Core Prompt Strategy

The system prompt must do two things that are easy to conflate but need to stay separate:

**Step 1 -- Semantic Reconstruction.** The transcription is garbled. The model's first job is to figure out what the speaker actually said. This is not grammar correction. "Eye want to start jogging" should become "I want to start jogging." "Grateful for my wife robin" should become "Grateful for my wife Robyn." The model should use phonetic similarity, context clues, and common sense to reconstruct meaning. Proper nouns (names, places, tools) are the hardest part.

**Step 2 -- Structured Extraction.** From the reconstructed text, extract into three categories. Each category uses a simple markdown format:

```markdown
## Thoughts

- [extracted thought 1]
- [extracted thought 2]

## Actions

- [ ] [extracted action 1]
- [ ] [extracted action 2]

## Gratitude

- [thing grateful for 1]
- [thing grateful for 2]
```

Actions use Obsidian checkbox format (`- [ ]`). If a category has no entries, omit the section entirely.

## Daily Note Integration

The tool appends to an existing daily note or creates one if it doesn't exist.

**File path:** `{vault_path}/{note_dir}/{YYYY-MM-DD}.md`

**Append behavior:** If the file exists, append a horizontal rule (`---`) followed by a `## Voice Journal` heading and the extracted content. If the file doesn't exist, create it with a minimal frontmatter block:

```markdown
---
date: 2026-03-03
---

## Voice Journal

[extracted content here]
```

**Do not overwrite** existing content in the daily note. Always append.

## Input File Handling

- Process all `.txt` files in the input directory by default
- Sort files by name (chronological if timestamped)
- After successful processing, optionally move files to a `processed/` subdirectory (future feature, not MVP)
- Skip files that are empty or contain only whitespace
- Log which files were processed and which were skipped

## Error Handling

- If the provider is unavailable (Ollama not running, bad API key), fail fast with a clear error message
- If a single file fails, log the error and continue processing remaining files
- If the vault path doesn't exist, error before processing any files
- If --dry-run, skip all file existence checks for the vault

## Testing Strategy

- Unit tests for extractor: provide known garbled input, assert categories are correctly extracted
- Unit tests for daily_note: test append-to-existing, create-new, and edge cases (missing directory)
- Integration tests for each provider: mock the API, verify prompt construction and response parsing
- Fixture files: include 3-5 real examples of garbled transcription with expected reconstructed output

## Dependencies

- `requests` (for Ollama HTTP API)
- `anthropic` (for Anthropic provider)
- `groq` (for Groq provider)
- `openai` (for DeepSeek provider, uses OpenAI-compatible API)
- `pytest` (dev dependency)
- No heavy frameworks. This is a CLI tool, not a web app.

## What Success Looks Like

```bash
$ python voice_journal.py --provider local --dry-run --file ~/Documents/Voice/memo.txt

--- Raw Transcription ---
eye am really grateful for robin and john john today we went to the park
and I was thinking about how I need to rite more about duck db for the blog
also need to call the pediatrition tomorrow

--- Reconstructed ---
I am really grateful for Robyn and Jon Jon today. We went to the park
and I was thinking about how I need to write more about DuckDB for the blog.
Also need to call the pediatrician tomorrow.

--- Extracted ---
## Thoughts
- Went to the park with Robyn and Jon Jon. Thinking about writing more DuckDB content for the blog.

## Actions
- [ ] Call the pediatrician tomorrow

## Gratitude
- Grateful for Robyn and Jon Jon
```

## Build Order

1. **Provider base class + local provider** -- get a single completion working via Ollama
2. **Extractor** -- system prompt + response parsing into the three categories
3. **Daily note writer** -- append/create logic
4. **CLI wiring** -- argparse, glue it together, --dry-run
5. **Additional providers** -- anthropic, groq, deepseek
6. **Tests** -- fixtures from real voice memos, unit tests for each module
7. **Polish** -- error handling, --verbose, edge cases

## Future Enhancements (Not MVP)

- Move processed files to `processed/` subdirectory
- Timestamp each voice journal entry within the daily note
- Support audio files directly (whisper transcription before extraction)
- Config file (`.voice-journal.toml`) for persistent settings
- Integration with the ModelClient abstraction from `local-ai-tools` toolkit once that stabilizes
