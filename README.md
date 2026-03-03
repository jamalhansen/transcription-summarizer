# Voice Journal

A CLI tool that reads poorly transcribed voice memo files, interprets what you actually meant, and extracts structured content into your Obsidian daily notes.

The core challenge is **semantic reconstruction** — not grammar cleanup, but meaning recovery from garbled transcriptions. "Eye want to rite more about duck db" becomes "I want to write more about DuckDB."

## What It Does

1. Reads `.txt` and `.md` transcription files from a configurable input directory
2. Sends each transcription to an LLM that reconstructs the intended meaning
3. Extracts three categories from the reconstructed text:
   - **Thoughts** — meaningful ideas, reflections, observations
   - **Actions** — future tasks and commitments (Obsidian checkbox format)
   - **Gratitude** — things you expressed genuine gratitude for
4. Groups all files from the same day and appends a single merged `## Voice Journal` section to your Obsidian daily note
5. Moves processed files to a `processed/` subdirectory

## Installation

Requires [uv](https://docs.astral.sh/uv/) and Python 3.12+.

```bash
git clone https://github.com/jamalhansen/transcription-summarizer.git
cd transcription-summarizer
uv sync
```

## Quick Start

```bash
# Preview output without writing anything (uses local Ollama by default)
uv run python voice_journal.py --dry-run

# Process and write to your Obsidian vault
uv run python voice_journal.py

# Use Anthropic's Claude instead
uv run python voice_journal.py --provider anthropic

# Process a single file
uv run python voice_journal.py --file ~/Documents/Voice/memo.txt --dry-run
```

## Providers

| Provider | Flag | Default Model | Requires |
|---|---|---|---|
| Ollama (local) | `--provider local` | `llama3.2:3b` | [Ollama](https://ollama.com) running locally |
| Anthropic | `--provider anthropic` | `claude-haiku-4-5-20251001` | `ANTHROPIC_API_KEY` |
| Groq | `--provider groq` | `llama-3.3-70b-versatile` | `GROQ_API_KEY` |
| DeepSeek | `--provider deepseek` | `deepseek-chat` | `DEEPSEEK_API_KEY` |

Override the model for any provider with `--model`:

```bash
uv run python voice_journal.py --provider local --model llama3.1:8b
uv run python voice_journal.py --provider anthropic --model claude-sonnet-4-5-20251001
```

If you specify an invalid model name, the tool will list known options and (for cloud providers) link to the official model docs.

## Configuration

### Environment Variables

| Variable | Purpose | Default |
|---|---|---|
| `OBSIDIAN_VAULT_PATH` | Path to your Obsidian vault | `~/vaults/BrainSync/` |
| `VOICE_JOURNAL_TEMPLATE` | Path to daily note template | `~/vaults/BrainSync/Templates/Daily Note.md` |
| `ANTHROPIC_API_KEY` | Anthropic API key | — |
| `GROQ_API_KEY` | Groq API key | — |
| `DEEPSEEK_API_KEY` | DeepSeek API key | — |
| `OLLAMA_HOST` | Ollama server URL | `http://localhost:11434` |

Add these to your shell profile or a `.env` file.

### Obsidian Template

When creating a new daily note, the tool renders your Obsidian template and appends the Voice Journal section after it. Supported template variables:

```
{{date:YYYY-MM-DD}}    → 2026-03-03
{{date:YYYY-[W]W}}     → 2026-W10
{{yesterday}}          → 2026-03-02
{{ tomorrow }}         → 2026-03-04
```

If no template is found, a minimal frontmatter block is used instead.

## CLI Reference

```
uv run python voice_journal.py [OPTIONS]
```

| Argument | Short | Default | Description |
|---|---|---|---|
| `--provider` | `-p` | `local` | LLM backend: `local`, `anthropic`, `groq`, `deepseek` |
| `--model` | `-m` | provider default | Override the model for the chosen provider |
| `--dry-run` | `-n` | false | Preview full note output without writing or moving files |
| `--input-dir` | `-i` | iCloud Documents/Voice/ | Directory containing transcription files |
| `--file` | `-f` | — | Process a single file instead of the whole directory |
| `--vault-path` | `-v` | `$OBSIDIAN_VAULT_PATH` | Path to your Obsidian vault root |
| `--note-dir` | `-d` | `Timeline` | Subdirectory within vault for daily notes |
| `--date` | | today | Override the date for the daily note (YYYY-MM-DD) |
| `--verbose` | | false | Print raw transcription and reconstructed text |

## Example Output

```
$ uv run python voice_journal.py --provider anthropic --dry-run --file memo.txt

Processing: memo.txt

--- Preview: 2026-03-03.md ---

## Voice Journal

## Thoughts
- The two vibe-coded LLM tools are flexible enough to run against local or frontier models.

## Actions
- [ ] Write a blog post about the automated personal knowledge workflow.

## Gratitude
- I'm grateful Justin came over for lunch today.
```

## Development

```bash
# Run tests
uv run pytest

# Run tests with output
uv run pytest -v
```

Tests are organized one file per module under `tests/`, with fixture files in `tests/fixtures/`. All external API calls are mocked.

## Project Structure

```
voice_journal.py        # CLI entrypoint
extractor.py            # LLM prompt + response parser
daily_note.py           # Obsidian note append/create + template rendering
config.py               # Defaults and path resolution
providers/
  base.py               # Abstract BaseProvider interface
  local.py              # Ollama
  anthropic_provider.py # Anthropic Claude
  groq_provider.py      # Groq
  deepseek_provider.py  # DeepSeek (OpenAI-compatible)
tests/
  test_extractor.py
  test_daily_note.py
  test_providers.py
  fixtures/
```
