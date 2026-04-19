#!/usr/bin/env python3
"""Voice Journal CLI — process garbled voice memo transcriptions into Obsidian daily notes."""

from datetime import date
from itertools import groupby
from pathlib import Path
from typing import Annotated, Optional

import typer

from .config import (
    DEFAULT_NOTE_DIR,
    DEFAULT_TEMPLATE_PATH,
    resolve_input_dir,
    resolve_vault_path,
)
from .extractor import ExtractionResult, extract
from local_first_common.config import get_setting
from local_first_common.obsidian import (
    append_to_daily_note,
    get_daily_note_path,
    render_obsidian_template,
)
from local_first_common.cli import (
    dry_run_option,
    no_llm_option,
    resolve_dry_run,
    resolve_provider,
)
from local_first_common.providers import PROVIDERS
from local_first_common.tracking import register_tool, timed_run

_TOOL = register_tool("transcription-summarizer")


class TranscriptionError(Exception):
    """Base typed error for transcription-summarizer."""


class ProviderSetupError(TranscriptionError):
    """Raised when provider resolution fails."""


class ExtractionError(TranscriptionError):
    """Raised when the LLM extraction call fails."""

app = typer.Typer(add_completion=False)


def get_note_path(
    vault_path: str, note_dir: str, note_date: date | None = None
) -> Path:
    """Return the path for a daily note file."""
    d = note_date or date.today()
    return get_daily_note_path(Path(vault_path), d, subdir=note_dir)


def append_to_note(
    note_path: Path, content: str, template_path: str | None = None
) -> None:
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
            rendered = render_obsidian_template(
                tpl.read_text(encoding="utf-8"), note_date
            )
            return rendered.rstrip() + "\n\n---\n\n"
    try:
        note_date = date.fromisoformat(note_path.stem[:10])
    except ValueError:
        note_date = date.today()
    return f"---\ndate: {note_date.isoformat()}\n---\n\n"


def collect_files(file: str | None, input_dir: str | None) -> list[Path]:
    if file:
        p = Path(file).expanduser()
        if not p.exists():
            typer.echo(f"Error: file not found: {p}", err=True)
            raise typer.Exit(1)
        return [p]

    resolved_dir = resolve_input_dir(input_dir)
    if not resolved_dir.exists():
        typer.echo(f"Error: input directory not found: {resolved_dir}", err=True)
        raise typer.Exit(1)

    files = sorted(
        f for f in resolved_dir.iterdir() if f.suffix in (".txt", ".md") and f.is_file()
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
        typer.echo(f"Skipping empty file: {file_path.name}")
        return None

    typer.echo(f"Processing: {file_path.name}")

    if verbose:
        typer.echo(f"\n--- Raw Transcription ---\n{raw.strip()}\n")

    try:
        with timed_run(
            "transcription-summarizer",
            getattr(provider, "model", None),
            source_location=str(file_path),
        ) as run:
            result = extract(provider, raw)
            run.item_count = 1
            run.input_tokens = getattr(provider, "input_tokens", None) or None
            run.output_tokens = getattr(provider, "output_tokens", None) or None
    except ExtractionError as e:
        typer.echo(f"Error processing {file_path.name}: {e}", err=True)
        return None
    except Exception as e:
        typer.echo(f"Error processing {file_path.name}: {e}", err=True)
        return None

    if verbose:
        typer.echo(f"--- Reconstructed ---\n{result.reconstructed}\n")

    return result


@app.command()
def main(
    provider: Annotated[
        Optional[str], typer.Option("--provider", "-p", help="LLM backend to use")
    ] = None,
    model: Annotated[
        Optional[str],
        typer.Option(
            "--model", "-m", help="Override the default model for the chosen provider"
        ),
    ] = None,
    dry_run: Annotated[bool, dry_run_option()] = False,
    no_llm: Annotated[bool, no_llm_option()] = False,
    input_dir: Annotated[
        Optional[str],
        typer.Option(
            "--input-dir",
            "-i",
            help="Directory containing voice transcription .txt files",
        ),
    ] = None,
    file: Annotated[
        Optional[str],
        typer.Option(
            "--file", "-f", help="Process a single file instead of the whole directory"
        ),
    ] = None,
    vault_path: Annotated[
        Optional[str],
        typer.Option("--vault-path", "-v", help="Path to the Obsidian vault root"),
    ] = None,
    note_dir: Annotated[
        str,
        typer.Option(
            "--note-dir",
            "-d",
            help=f"Subdirectory within vault for daily notes (default: {DEFAULT_NOTE_DIR})",
        ),
    ] = DEFAULT_NOTE_DIR,
    override_date: Annotated[
        Optional[str],
        typer.Option(
            "--date", help="Override the date for the daily note (YYYY-MM-DD)"
        ),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            help="Print raw transcription and reconstructed text before extraction",
        ),
    ] = False,
    all_files: Annotated[
        bool,
        typer.Option(
            "--all",
            help="Combine all transcriptions into a single extraction for today's note",
        ),
    ] = False,
) -> None:
    _TOOL_NAME = "transcription-summarizer"
    provider = get_setting(_TOOL_NAME, "provider", cli_val=provider, default="local")
    model = get_setting(_TOOL_NAME, "model", cli_val=model, default=None)
    if not all_files:
        all_files = bool(get_setting(_TOOL_NAME, "all", default=False))

    if provider not in PROVIDERS:
        typer.echo(
            f"Error: unknown provider '{provider}'. Choose from: {', '.join(PROVIDERS.keys())}",
            err=True,
        )
        raise typer.Exit(1)

    dry_run = resolve_dry_run(dry_run, no_llm)

    # Resolve note date
    note_date = None
    if override_date:
        try:
            note_date = date.fromisoformat(override_date)
        except ValueError:
            typer.echo(
                f"Error: invalid date format '{override_date}'. Use YYYY-MM-DD.",
                err=True,
            )
            raise typer.Exit(1)

    # Validate vault path unless dry-run
    resolved_vault = resolve_vault_path(vault_path)
    if not dry_run and not resolved_vault.exists():
        typer.echo(f"Error: vault path not found: {resolved_vault}", err=True)
        raise typer.Exit(1)

    # Build provider
    try:
        llm_provider = resolve_provider(PROVIDERS, provider, model, no_llm=no_llm)
    except ProviderSetupError as e:
        typer.echo(f"Error initializing provider '{provider}': {e}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Error initializing provider '{provider}': {e}", err=True)
        raise typer.Exit(1)

    files = collect_files(file, input_dir)
    if not files:
        typer.echo("No .txt or .md files found to process.")
        raise typer.Exit(0)

    fallback_date = note_date or date.today()
    results: list[tuple[Path, date, ExtractionResult]] = []
    skipped = 0

    for f in files:
        result = process_file(f, llm_provider, verbose)
        if result is not None:
            results.append((f, file_date(f, fallback_date), result))
        else:
            skipped += 1

    if dry_run:
        dry_groups: list[tuple[date, list]] = (
            [(fallback_date, results)]
            if all_files
            else [(d, list(g)) for d, g in groupby(results, key=lambda x: x[1])]
        )
        for d, group in dry_groups:
            n_path = get_note_path(str(resolved_vault), note_dir, d)
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
                preview = (
                    existing.rstrip() + "\n\n---\n\n## Voice Journal\n\n" + md + "\n"
                )
            else:
                base = new_note_base(n_path, DEFAULT_TEMPLATE_PATH)
                preview = base + "## Voice Journal\n\n" + md + "\n"
            typer.echo(f"\n--- Preview: {n_path.name} ---\n")
            typer.echo(preview)
    else:
        if all_files:
            combined = ExtractionResult(reconstructed="")
            for _, _, result in results:
                combined.thoughts.extend(result.thoughts)
                combined.actions.extend(result.actions)
                combined.gratitude.extend(result.gratitude)
            md = combined.to_markdown()
            if md:
                n_path = get_note_path(str(resolved_vault), note_dir, fallback_date)
                append_to_note(n_path, md, template_path=DEFAULT_TEMPLATE_PATH)
                typer.echo(f"  Written to: {n_path}")
            for f, _, _ in results:
                processed_dir = f.parent / "processed"
                processed_dir.mkdir(exist_ok=True)
                dest = processed_dir / f.name
                f.rename(dest)
                typer.echo(f"  Moved to:   {dest}")
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
                    n_path = get_note_path(str(resolved_vault), note_dir, d)
                    append_to_note(n_path, md, template_path=DEFAULT_TEMPLATE_PATH)
                    typer.echo(f"  Written to: {n_path}")

                for f, _, _ in group:
                    processed_dir = f.parent / "processed"
                    processed_dir.mkdir(exist_ok=True)
                    dest = processed_dir / f.name
                    f.rename(dest)
                    typer.echo(f"  Moved to:   {dest}")

    typer.echo(f"\nDone. Processed: {len(results)}, Skipped: {skipped}")


if __name__ == "__main__":
    app()
