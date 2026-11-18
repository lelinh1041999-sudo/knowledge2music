"""Validate educational lyrics and collect citations returned by Gemini."""

import json
import re
from urllib.parse import urlsplit


SONG_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["ready", "needs_info"]},
        "message": {"type": "string", "description": "Explain the missing information when status is needs_info."},
        "title": {"type": "string"},
        "summary": {"type": "string"},
        "tags": {"type": "string"},
        "lyrics": {"type": "string"},
    },
    "required": ["status", "message", "title", "summary", "tags", "lyrics"],
    "additionalProperties": False,
}


def song_is_ready(song):
    return (
        isinstance(song, dict)
        and all(isinstance(song.get(key), str) and song[key].strip() for key in ("title", "summary", "tags", "lyrics"))
        and re.search(r"(?im)^\s*\[(?:verse|chorus)(?:\s+\d+)?\]\s*", song["lyrics"]) is not None
    )


def parse_song_response(text):
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.I)
    result = json.loads(text)
    if not isinstance(result, dict) or any(not isinstance(result.get(key), str) for key in SONG_SCHEMA["required"]):
        raise ValueError("The response is missing required song fields.")
    result = {key: result[key].strip() for key in SONG_SCHEMA["required"]}
    if result["status"] == "needs_info" and result["message"]:
        return result
    if result["status"] != "ready" or not song_is_ready(result):
        raise ValueError("The response does not contain a complete song.")
    return result


def search_attributions(interaction):
    data = interaction.model_dump(exclude_none=True)
    sources = {}
    suggestions = []
    for step in data.get("steps", []):
        if step.get("type") == "google_search_result":
            for item in step.get("result", []):
                html = item.get("search_suggestions")
                if html and html not in suggestions:
                    suggestions.append(html)
        if step.get("type") == "model_output":
            for block in step.get("content", []):
                for annotation in block.get("annotations", []):
                    url = annotation.get("url", "")
                    if annotation.get("type") == "url_citation" and urlsplit(url).scheme in {"http", "https"}:
                        sources[url] = annotation.get("title") or urlsplit(url).hostname
    return [{"url": url, "title": title} for url, title in sources.items()], suggestions
