"""Shared Azure AI Foundry client. Every LLM-calling agent (Summarize,
Simplify, Translate, Insight, Ask AI) goes through call_llm() instead of
constructing its own client — see CLAUDE.md Section 6.

transcribe_audio() is the one exception: it's a SEPARATE Azure resource
from the one above (confirmed with Varun 2026-08-20 — not
beyondportal-foundry, likely because gpt-4o-transcribe-diarize isn't
available there), so it gets its own client — see CLAUDE.md Section 6 #9."""

from openai import AzureOpenAI, OpenAI, OpenAIError

from config import settings

_client = OpenAI(
    base_url=settings.foundry_endpoint,
    api_key=settings.foundry_api_key,
)

_transcribe_client: OpenAI | AzureOpenAI | None = None


def call_llm(system_prompt: str, user_prompt: str) -> str:
    """Send a single chat completion request to the Foundry deployment.

    Raises RuntimeError on failure so callers can turn it into a clean
    error response instead of letting the API crash.
    """
    try:
        response = _client.chat.completions.create(
            model=settings.foundry_deployment_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
    except OpenAIError as exc:
        raise RuntimeError("Foundry LLM call failed") from exc

    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("Foundry LLM call returned an empty response")
    return content


def _get_transcribe_client() -> OpenAI | AzureOpenAI:
    global _transcribe_client
    if not settings.foundry_transcribe_endpoint or not settings.foundry_transcribe_api_key \
            or not settings.foundry_transcribe_deployment_name:
        raise RuntimeError(
            "Video transcription is not configured — set FOUNDRY_TRANSCRIBE_ENDPOINT, "
            "FOUNDRY_TRANSCRIBE_API_KEY, and FOUNDRY_TRANSCRIBE_DEPLOYMENT_NAME in .env "
            "(CLAUDE.md Section 6 #9)."
        )
    if _transcribe_client is None:
        if settings.foundry_legacy_api_version:
            _transcribe_client = AzureOpenAI(
                azure_endpoint=settings.foundry_transcribe_endpoint,
                api_key=settings.foundry_transcribe_api_key,
                api_version=settings.foundry_legacy_api_version,
            )
        else:
            _transcribe_client = OpenAI(
                base_url=settings.foundry_transcribe_endpoint.rstrip("/") + "/openai/v1/",
                api_key=settings.foundry_transcribe_api_key,
            )
    return _transcribe_client


def transcribe_audio(audio_bytes: bytes, filename: str) -> str:
    """Transcribe video/audio bytes via the dedicated transcription
    resource. Raises RuntimeError if not configured yet, or if the call
    fails."""
    client = _get_transcribe_client()
    try:
        result = client.audio.transcriptions.create(
            model=settings.foundry_transcribe_deployment_name,
            file=(filename, audio_bytes),
            chunking_strategy="auto",  # required by diarization models
        )
    except OpenAIError as exc:
        raise RuntimeError("Foundry transcription call failed") from exc
    return result.text
