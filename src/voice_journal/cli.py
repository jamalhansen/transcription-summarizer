#!/usr/bin/env python3
"""Voice Journal CLI — process garbled voice memo transcriptions into Obsidian daily notes."""

from datetime import date, datetime
from itertools import groupby
from pathlib import Path
from typing import Annotated

import typer
from local_first_common.cli import (
    dry_run_option,
    no_llm_option,
    resolve_dry_run,
    resolve_provider,
)
from local_first_common.config import get_setting
from local_first_common.providers import PROVIDERS
from local_first_common.tracking import register_tool, timed_run

from .config import (
    DEFAULT_NOTE_DIR,
    DEFAULT_TEMPLATE_PATH,
    resolve_input_dir,
    resolve_vault_path,
)
from .core import (
    AudioTranscribeError,
    ExtractionError,
    ProviderSetupError,
    append_to_note,
    file_date,
    get_note_path,
    new_note_base,
)
from .extractor import ExtractionResult, extract
from .transcribe import AUDIO_EXTENSIONS, DEFAULT_WHISPER_MODEL, transcribe_audio

_TOOL = register_tool("transcription-summarizer")

app = typer.Typer(add_completion=False)


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
        f
        for f in resolved_dir.iterdir()
        if f.suffix in (".txt", ".md", *AUDIO_EXTENSIONS) and f.is_file()
    )
    return files


def process_file(file_path: Path, provider, verbose: bool, whisper_model: str):
    """Extract content from a transcription (or audio) file. Returns ExtractionResult or None."""
    if file_path.suffix in AUDIO_EXTENSIONS:
        typer.echo(f"Transcribing: {file_path.name}")
        try:
            raw = transcribe_audio(file_path, model=whisper_model)
        except AudioTranscribeError as e:
            typer.echo(f"Error transcribing {file_path.name}: {e}", err=True)
            return None
    else:
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
    except Exception as e:  # noqa: BLE001 - top-level per-file boundary: report and skip, don't crash the whole batch
        typer.echo(f"Error processing {file_path.name}: {e}", err=True)
        return None

    if verbose:
        typer.echo(f"--- Reconstructed ---\n{result.reconstructed}\n")

    return result


def archive_file(f: Path, result: ExtractionResult) -> Path:
    """Move a processed input into its own processed/ subfolder.

    For audio input, also writes the transcript alongside it -- for a text/md
    input the transcript *was* the file, so there's nothing extra to save.
    """
    processed_dir = f.parent / "processed"
    processed_dir.mkdir(exist_ok=True)
    dest = processed_dir / f.name
    f.rename(dest)
    if f.suffix in AUDIO_EXTENSIONS and result.reconstructed:
        (processed_dir / f"{f.stem}.txt").write_text(result.reconstructed, encoding="utf-8")
    return dest


@app.command()
def main(
    provider: Annotated[
        str | None, typer.Option("--provider", "-p", help="LLM backend to use")
    ] = None,
    model: Annotated[
        str | None,
        typer.Option(
            "--model", "-m", help="Override the default model for the chosen provider"
        ),
    ] = None,
    dry_run: Annotated[bool, dry_run_option()] = False,
    no_llm: Annotated[bool, no_llm_option()] = False,
    input_dir: Annotated[
        str | None,
        typer.Option(
            "--input-dir",
            "-i",
            help="Directory containing voice transcription .txt files",
        ),
    ] = None,
    file: Annotated[
        str | None,
        typer.Option(
            "--file", "-f", help="Process a single file instead of the whole directory"
        ),
    ] = None,
    vault_path: Annotated[
        str | None,
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
        str | None,
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
    whisper_model: Annotated[
        str | None,
        typer.Option(
            "--whisper-model",
            help="Local Whisper model (mlx-whisper) used to transcribe audio input files",
        ),
    ] = None,
) -> None:
    _TOOL_NAME = "transcription-summarizer"
    provider = get_setting(_TOOL_NAME, "provider", cli_val=provider, default="local")
    model = get_setting(
        _TOOL_NAME,
        "model",
        cli_val=model,
        default="llama3.2:3b" if provider in ("local", "ollama") else None,
    )
    whisper_model = get_setting(
        _TOOL_NAME, "whisper_model", cli_val=whisper_model, default=DEFAULT_WHISPER_MODEL
    )
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
    except Exception as e:  # noqa: BLE001 - top-level CLI boundary: report cleanly and exit, don't show a raw traceback
        typer.echo(f"Error initializing provider '{provider}': {e}", err=True)
        raise typer.Exit(1)

    files = collect_files(file, input_dir)
    if not files:
        typer.echo("No .txt, .md, or audio files found to process.")
        raise typer.Exit(0)

    fallback_date = note_date or datetime.now().astimezone().date()
    results: list[tuple[Path, date, ExtractionResult]] = []
    skipped = 0

    for f in files:
        result = process_file(f, llm_provider, verbose, whisper_model)
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
            for f, _, result in results:
                dest = archive_file(f, result)
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

                for f, _, result in group:
                    dest = archive_file(f, result)
                    typer.echo(f"  Moved to:   {dest}")

    typer.echo(f"\nDone. Processed: {len(results)}, Skipped: {skipped}")


if __name__ == "__main__":
    app()
