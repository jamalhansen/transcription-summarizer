#!/usr/bin/env python3
"""Voice Journal CLI — process garbled voice memo transcriptions into Obsidian daily notes."""

import argparse
import sys
from datetime import date
from itertools import groupby
from pathlib import Path

from config import DEFAULT_NOTE_DIR, DEFAULT_TEMPLATE_PATH, resolve_input_dir, resolve_vault_path
from extractor import ExtractionResult, extract
from local_first_common.obsidian import (
    append_to_daily_note,
    get_daily_note_path,
    render_obsidian_template,
)
from local_first_common.providers import (
    AnthropicProvider,
    DeepSeekProvider,
    GroqProvider,
    OllamaProvider,
)

# Map "local" -> OllamaProvider to preserve the original CLI default naming.
PROVIDERS = {
    "local": OllamaProvider,
    "anthropic": AnthropicProvider,
    "groq": GroqProvider,
    "deepseek": DeepSeekProvider,
}


def get_note_path(vault_path: str, note_dir: str, note_date: date | None = None) -> Path:
    """Return the path for a daily note file."""
    d = note_date or date.today()
    return get_daily_note_path(Path(vault_path), d, subdir=note_dir)


def append_to_note(note_path: Path, content: str, template_path: str | None = None) -> None:
    """Append a Voice Journal section to an existing or new daily note."""
    tpl = Path(template_path).expanduser() if template_path else None
    append_to_daily_note(
        note_path,
        "## Voice Journal\n\n" + content,
        template_path=tpl,
    )


def new_note_base(note_path: Path, template_path: str | None) -> str:
    """Return the base content for a new note (rendered template or fallback frontmatter)."""
    if template_path:
        tpl = Path(template_path).expanduser()
        if tpl.exists():
            try:
                note_date = date.fromisoformat(note_path.stem[:10])
            except ValueError:
                note_date = date.today()
            rendered = render_obsidian_template(tpl.read_text(encoding="utf-8"), note_date)
            return rendered.rstrip() + "\n\n---\n\n"
    return f"---\ndate: {date.today().isoformat()}\n---\n\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract structured content from voice memo transcriptions into Obsidian daily notes."
    )
    parser.add_argument(
        "--provider", "-p",
        default="local",
        choices=list(PROVIDERS.keys()),
        help="LLM backend to use (default: local)",
    )
    parser.add_argument(
        "--model", "-m",
        default=None,
        help="Override the default model for the chosen provider",
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Print output to stdout instead of writing to file",
    )
    parser.add_argument(
        "--input-dir", "-i",
        default=None,
        help="Directory containing voice transcription .txt files",
    )
    parser.add_argument(
        "--file", "-f",
        default=None,
        help="Process a single file instead of the whole directory",
    )
    parser.add_argument(
        "--vault-path", "-v",
        default=None,
        help="Path to the Obsidian vault root",
    )
    parser.add_argument(
        "--note-dir", "-d",
        default=DEFAULT_NOTE_DIR,
        help=f"Subdirectory within vault for daily notes (default: {DEFAULT_NOTE_DIR})",
    )
    parser.add_argument(
        "--date",
        default=None,
        help="Override the date for the daily note (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print raw transcription and reconstructed text before extraction",
    )
    return parser


def collect_files(args) -> list[Path]:
    if args.file:
        p = Path(args.file).expanduser()
        if not p.exists():
            print(f"Error: file not found: {p}", file=sys.stderr)
            sys.exit(1)
        return [p]

    input_dir = resolve_input_dir(args.input_dir)
    if not input_dir.exists():
        print(f"Error: input directory not found: {input_dir}", file=sys.stderr)
        sys.exit(1)

    files = sorted(
        f for f in input_dir.iterdir()
        if f.suffix in (".txt", ".md") and f.is_file()
    )
    return files


def file_date(file_path: Path, fallback: date) -> date:
    """Extract date from filename (YYYY-MM-DD prefix) or fall back to provided date."""
    try:
        return date.fromisoformat(file_path.stem[:10])
    except ValueError:
        return fallback


def process_file(file_path: Path, provider, verbose: bool):
    """Extract content from a transcription file. Returns ExtractionResult or None."""
    raw = file_path.read_text(encoding="utf-8")

    if not raw.strip():
        print(f"Skipping empty file: {file_path.name}")
        return None

    print(f"Processing: {file_path.name}")

    if verbose:
        print(f"\n--- Raw Transcription ---\n{raw.strip()}\n")

    try:
        result = extract(provider, raw)
    except Exception as e:
        print(f"Error processing {file_path.name}: {e}", file=sys.stderr)
        return None

    if verbose:
        print(f"--- Reconstructed ---\n{result.reconstructed}\n")

    return result


def main():
    parser = build_parser()
    args = parser.parse_args()

    # Resolve note date
    note_date = None
    if args.date:
        try:
            note_date = date.fromisoformat(args.date)
        except ValueError:
            print(f"Error: invalid date format '{args.date}'. Use YYYY-MM-DD.", file=sys.stderr)
            sys.exit(1)

    # Validate vault path unless dry-run
    vault_path = resolve_vault_path(args.vault_path)
    if not args.dry_run and not vault_path.exists():
        print(f"Error: vault path not found: {vault_path}", file=sys.stderr)
        sys.exit(1)

    note_path = get_note_path(str(vault_path), args.note_dir, note_date)

    # Build provider
    provider_cls = PROVIDERS[args.provider]
    try:
        provider = provider_cls(model=args.model)
    except Exception as e:
        print(f"Error initializing provider '{args.provider}': {e}", file=sys.stderr)
        sys.exit(1)

    files = collect_files(args)
    if not files:
        print("No .txt or .md files found to process.")
        sys.exit(0)

    fallback_date = note_date or date.today()
    results = []  # (file_path, file_date, extraction_result)
    skipped = 0

    for f in files:
        result = process_file(f, provider, args.verbose)
        if result is not None:
            results.append((f, file_date(f, fallback_date), result))
        else:
            skipped += 1

    if args.dry_run:
        for d, group in groupby(results, key=lambda x: x[1]):
            n_path = get_note_path(str(vault_path), args.note_dir, d)
            combined = ExtractionResult(reconstructed="")
            for _, _, result in group:
                combined.thoughts.extend(result.thoughts)
                combined.actions.extend(result.actions)
                combined.gratitude.extend(result.gratitude)
            md = combined.to_markdown()
            if not md:
                continue
            if n_path.exists():
                existing = n_path.read_text(encoding="utf-8")
                preview = existing.rstrip() + "\n\n---\n\n## Voice Journal\n\n" + md + "\n"
            else:
                base = new_note_base(n_path, DEFAULT_TEMPLATE_PATH)
                preview = base + "## Voice Journal\n\n" + md + "\n"
            print(f"\n--- Preview: {n_path.name} ---\n")
            print(preview)
    else:
        for d, group in groupby(results, key=lambda x: x[1]):
            group = list(group)
            combined = ExtractionResult(reconstructed="")
            for _, _, result in group:
                combined.thoughts.extend(result.thoughts)
                combined.actions.extend(result.actions)
                combined.gratitude.extend(result.gratitude)
            md = combined.to_markdown()
            if md:
                n_path = get_note_path(str(vault_path), args.note_dir, d)
                append_to_note(n_path, md, template_path=DEFAULT_TEMPLATE_PATH)
                print(f"  Written to: {n_path}")

            for f, _, _ in group:
                processed_dir = f.parent / "processed"
                processed_dir.mkdir(exist_ok=True)
                dest = processed_dir / f.name
                f.rename(dest)
                print(f"  Moved to:   {dest}")

    print(f"\nDone. Processed: {len(results)}, Skipped: {skipped}")


if __name__ == "__main__":
    main()
