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
- Do not invent content. Only include what was actually said. This is the single most
  important rule: if you are not sure what the speaker meant, or the transcript is too
  short or fragmentary to say anything definite about, do NOT fill the gap with invented
  people, events, hobbies, dates, or backstory to make the entry feel complete. A short,
  literal restatement of a fragment is correct; a fabricated story built around that
  fragment is a serious error, even if it reads more naturally.
- If the entry is just a single passing thought, a short paragraph is a complete, correct
  output -- don't pad it with a heading or bullets it doesn't need.
- Don't comment on the transcript, describe what you did, or add a title. Output only the
  finished journal entry itself.
"""

# A small local model has been observed to fabricate an entire elaborate journal entry
# (invented hobbies, invented specific dates, invented events) from a 3-word placeholder
# transcript, directly violating the prompt's own "do not invent content" rule above.
# Prompting alone did not stop it. Below this word count, there is not enough material
# for headers/bullets/checkboxes to add real value anyway, so skip the LLM rewrite
# entirely and pass the transcript through -- this removes the invention risk outright
# rather than trusting the model to follow the instruction.
MIN_WORDS_FOR_LLM_EDIT = 4

# Second, cheap guard for transcripts that do clear the word-count floor: the same
# failure mode (a short transcript turned into a much longer fabricated entry) is
# still possible above that floor. A real cleanup pass can legitimately grow a
# transcript somewhat (filler removed, structure added), but not by this much.
# Scoped to short raw transcripts only, so a genuinely long, expansive real ramble
# reformatted into structured bullets doesn't trip this guard.
MAX_EXPANSION_RATIO = 4.0
SHORT_TRANSCRIPT_CHARS = 200


def extract(provider: BaseProvider, transcription: str) -> str:
    """Send a transcript to the provider and return a cleaned, formatted journal entry.

    See MIN_WORDS_FOR_LLM_EDIT and MAX_EXPANSION_RATIO above for the guards against a
    demonstrated hallucination failure mode: a small local model inventing content for
    thin input instead of saying there's nothing to work with. An empty rewrite of
    non-empty input falls back to the transcript for the same reason: losing a real
    memo is worse than showing it unedited.
    """
    transcription = transcription.strip()
    if len(transcription.split()) < MIN_WORDS_FOR_LLM_EDIT:
        return transcription

    response = provider.complete(SYSTEM_PROMPT, transcription).strip()

    # An empty rewrite of non-empty real input is a different flavor of the same
    # problem -- the model failed to do its job -- and losing the memo entirely
    # is worse than showing the raw transcript.
    if not response:
        return transcription

    if (
        len(transcription) < SHORT_TRANSCRIPT_CHARS
        and len(response) > len(transcription) * MAX_EXPANSION_RATIO
    ):
        return transcription

    return response
