import re
from dataclasses import dataclass, field

from local_first_common.providers.base import BaseProvider

SYSTEM_PROMPT = """\
You are a voice memo interpreter. Your job is to process poorly transcribed voice memos in two steps.

STEP 1 — SEMANTIC RECONSTRUCTION
The transcription is garbled. Using phonetic similarity, context clues, and common sense, reconstruct what the speaker actually said. This is not grammar correction — it is meaning recovery. Pay special attention to proper nouns (names, places, tools, brands) which are often badly mangled. Output this as "Reconstructed:" followed by the corrected text.

IMPORTANT — Known proper nouns (always use these exact spellings):
- The speaker's child is named "Jon" (also called "Jon Jon"). NEVER write "John".

STEP 2 — STRUCTURED EXTRACTION
From the reconstructed text, extract content into up to three categories:

**Thoughts** — meaningful ideas, reflections, or observations worth remembering
**Actions** — future tasks or commitments I still need to do (not things already done)
**Gratitude** — specific things I expressed genuine gratitude for

Write all extracted items in first person, as if I am writing in my own journal. Use "I", not "The speaker" or "They".

Output the extracted content in this exact markdown format:

Reconstructed:
<reconstructed text here>

## Thoughts

- [thought 1]
- [thought 2]

## Actions

- [ ] [action 1]
- [ ] [action 2]

## Gratitude

- [thing grateful for]

Rules:
- Omit any section that has no entries. Do not output a heading with nothing under it.
- Do not invent content. Only extract what was actually expressed.
- Actions use `- [ ]` format exactly.
- Actions are future-only — things I still need to do. Never include past events or things already completed.
- Keep each item to one concise sentence. No padding or filler.
- Consolidate related ideas into a single item — do not repeat the same concept in different words.
- Actions must be concrete and specific. Skip vague intentions like "consider X", "think about Y", or "add to list".
- Thoughts should be meaningful insights or observations, not restatements of actions.
- Gratitude must be specific and personal. Skip generic or abstract entries.
"""

# Items that are clearly artifacts or placeholders — filter these out
_JUNK_PATTERNS = [
    r"^\[.*\]$",               # [thing grateful for 1], [action 1], etc.
    r"^nothing[\w\s]*$",       # nothing, nothing mentioned, nothing to add
    r"^none[\w\s]*$",          # none, none mentioned, none expressed
    r"^not[\w\s]*mentioned$",  # not mentioned, not explicitly mentioned
    r"^n/?a$",
    r"^-$",
]
_JUNK_RE = re.compile("|".join(_JUNK_PATTERNS), re.IGNORECASE)


def _is_junk(item: str) -> bool:
    return bool(_JUNK_RE.match(item.strip()))


@dataclass
class ExtractionResult:
    reconstructed: str
    thoughts: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    gratitude: list[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        sections = []
        if self.thoughts:
            sections.append("## Thoughts\n\n" + "\n".join(f"- {t}" for t in self.thoughts))
        if self.actions:
            sections.append("## Actions\n\n" + "\n".join(f"- [ ] {a}" for a in self.actions))
        if self.gratitude:
            sections.append("## Gratitude\n\n" + "\n".join(f"- {g}" for g in self.gratitude))
        return "\n\n".join(sections)


def extract(provider: BaseProvider, transcription: str) -> ExtractionResult:
    """Send transcription to the provider and parse the structured response."""
    response = provider.complete(SYSTEM_PROMPT, transcription)
    return _parse_response(response)


def _parse_response(response: str) -> ExtractionResult:
    """Parse the LLM response into an ExtractionResult."""
    reconstructed = ""
    thoughts: list[str] = []
    actions: list[str] = []
    gratitude: list[str] = []

    current_section = None
    lines = response.splitlines()

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("Reconstructed:"):
            current_section = "reconstructed"
            inline = stripped[len("Reconstructed:"):].strip()
            if inline:
                reconstructed = inline
            continue

        if stripped == "## Thoughts":
            current_section = "thoughts"
            continue
        if stripped == "## Actions":
            current_section = "actions"
            continue
        if stripped == "## Gratitude":
            current_section = "gratitude"
            continue

        if not stripped:
            if current_section == "reconstructed":
                current_section = None
            continue

        if current_section == "reconstructed":
            reconstructed = (reconstructed + " " + stripped).strip() if reconstructed else stripped
        elif current_section == "thoughts" and stripped.startswith("- "):
            item = stripped[2:].strip()
            if not _is_junk(item):
                thoughts.append(item)
        elif current_section == "actions" and stripped.startswith("- [ ] "):
            item = stripped[6:].strip()
            if not _is_junk(item):
                actions.append(item)
        elif current_section == "actions" and stripped.startswith("- "):
            # tolerate missing checkbox
            item = stripped[2:].strip()
            if not _is_junk(item):
                actions.append(item)
        elif current_section == "gratitude" and stripped.startswith("- "):
            item = stripped[2:].strip()
            if not _is_junk(item):
                gratitude.append(item)

    return ExtractionResult(
        reconstructed=reconstructed,
        thoughts=thoughts,
        actions=actions,
        gratitude=gratitude,
    )
