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
uv run python src/main.py --dry-run

# Process and write to your Obsidian vault
uv run python src/main.py

# Use Anthropic's Claude instead
uv run python src/main.py --provider anthropic

# Process a single file
uv run python src/main.py --file ~/Documents/Voice/memo.txt --dry-run
```

## Providers

All tools in this series share a common set of CLI flags for model management via [local-first-common](https://github.com/jamalhansen/local-first-common).

| Provider | Flag | Default Model | Requires |
|---|---|---|---|
| Ollama (local) | `--provider ollama` | `phi4-mini` | [Ollama](https://ollama.com) running locally |
| Anthropic | `--provider anthropic` | `claude-3-5-haiku-latest` | `ANTHROPIC_API_KEY` |
| Groq | `--provider groq` | `llama-3.3-70b-versatile` | `GROQ_API_KEY` |
| DeepSeek | `--provider deepseek` | `deepseek-chat` | `DEEPSEEK_API_KEY` |

Override the model for any provider with `--model`:

```bash
uv run python src/main.py --provider ollama --model llama3.2:3b
uv run python src/main.py --provider anthropic --model claude-3-5-sonnet-latest
```

## Configuration

### Environment Variables

| Variable | Purpose | Default |
|---|---|---|
| `OBSIDIAN_VAULT_PATH` | Path to your Obsidian vault | `~/vaults/BrainSync/` |
| `VOICE_JOURNAL_TEMPLATE` | Path to daily note template | `~/vaults/BrainSync/Templates/Daily Note.md` |
| `ANTHROPIC_API_KEY` | Anthropic API key | — |
| `GROQ_API_KEY` | Groq API key | — |
| `DEEPSEEK_API_KEY` | DeepSeek API key | — |

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
uv run python src/main.py [OPTIONS]
```

| Argument | Short | Default | Description |
|---|---|---|---|
| `--provider` | `-p` | `ollama` | LLM backend: `ollama`, `anthropic`, `groq`, `deepseek`, `gemini` |
| `--model` | `-m` | provider default | Override the model for the chosen provider |
| `--dry-run` | `-n` | false | Preview full note output without writing or moving files |
| `--input-dir` | `-i` | iCloud Documents/Voice/ | Directory containing transcription files |
| `--file` | `-f` | — | Process a single file instead of the whole directory |
| `--vault-path` | `-v` | `$OBSIDIAN_VAULT_PATH` | Path to your Obsidian vault root |
| `--note-dir` | `-d` | `Timeline` | Subdirectory within vault for daily notes |
| `--date` | | today | Override the date for the daily note (YYYY-MM-DD) |
| `--verbose` | | false | Show extra debug output |
| `--debug` | | false | Show raw prompts and LLM responses |

## Example Output

```
$ uv run python src/main.py --provider anthropic --dry-run --file memo.txt

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

This tool follows the [Local-First AI project blueprint](https://github.com/jamalhansen/local-first-common).

```
transcription-summarizer/
├── src/
│   ├── main.py          # Typer CLI entry point
│   ├── logic.py         # Core processing logic
│   ├── schema.py        # Pydantic output models
│   ├── prompts.py       # System and user prompt builders
│   ├── display.py       # Rich-based terminal formatting
│   ├── config.py        # Defaults and path resolution
│   ├── extractor.py     # LLM response parser
│   └── daily_note.py    # Obsidian note management
├── pyproject.toml       # Managed by uv
└── tests/
    ├── test_main.py     # CLI integration tests via MockProvider
    └── ...
```
