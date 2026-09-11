from local_first_common.providers.base import BaseProvider

SYSTEM_PROMPT = """\
You are editing a voice journal transcript into a clean, well-formatted journal entry.

The transcript is spoken, first-person, and mostly accurate (transcribed by Whisper) but
may still contain filler words, false starts, minor transcription slips, or run-on
sentences from natural speech. Lightly edit for readability without changing the meaning
or adding anything that wasn't said.

IMPORTANT — Known proper nouns (always use these exact spellings):
- The speaker's child is named "Jon" (also called "Jon Jon"). NEVER write "John".

Format the result as clean markdown, in first person ("I", not "the speaker" or "they"):
- Use a "## " heading only if the entry genuinely covers more than one distinct topic.
- Use bullet points for anything that's naturally a list.
- Mark concrete commitments or future tasks with a "- [ ] " checkbox -- not vague
  intentions like "I should think about X", only things I actually committed to doing.
- Write everything else as normal prose paragraphs. Don't force reflections, observations,
  or stories into bullet points just because they came from speech.

Rules:
- Do not invent content. Only include what was actually said.
- If the entry is just a single passing thought, a short paragraph is a complete, correct
  output -- don't pad it with a heading or bullets it doesn't need.
- Don't comment on the transcript, describe what you did, or add a title. Output only the
  finished journal entry itself.
"""


def extract(provider: BaseProvider, transcription: str) -> str:
    """Send a transcript to the provider and return a cleaned, formatted journal entry."""
    response = provider.complete(SYSTEM_PROMPT, transcription)
    return response.strip()
