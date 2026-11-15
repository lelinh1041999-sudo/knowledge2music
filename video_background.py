"""Generate a short background clip using Lightricks' public ZeroGPU Space."""

import json
import time
from urllib.parse import urljoin, urlsplit

import requests


SPACE_HOST = "lightricks-ltx-2-5.hf.space"
SPACE_URL = f"https://{SPACE_HOST}"
RUN_URL = f"{SPACE_URL}/gradio_api/call/run"
MAX_CLIP_BYTES = 16 * 1024 * 1024


def generate_background(prompt):
    # Anonymous access uses the Space's free public quota without a billing account.
    with requests.Session() as session:
        response = session.post(
            RUN_URL,
            json={"data": [prompt, None, 512, 896, 2.0, 42, "conv", False, True, False]},
            timeout=(10, 20),
        )
        response.raise_for_status()
        task_id = response.json()["event_id"]

        deadline = time.monotonic() + 180
        payload = None
        event = ""
        with session.get(f"{RUN_URL}/{task_id}", stream=True, timeout=(10, 60)) as queue:
            queue.raise_for_status()
            for raw in queue.iter_lines(chunk_size=128):
                if time.monotonic() > deadline:
                    raise TimeoutError("The public GPU queue took too long.")
                line = raw.decode("utf-8", errors="replace")
                if line.startswith("event:"):
                    event = line[6:].strip()
                elif line.startswith("data:") and event in {"error", "complete"}:
                    payload = json.loads(line[5:].strip())
                    break

        if event == "error":
            detail = payload.get("error") if isinstance(payload, dict) else None
            raise RuntimeError(str(detail or "The public video model could not generate a clip.")[:250])
        if not isinstance(payload, list) or not payload or not isinstance(payload[0], dict):
            raise RuntimeError("The public video model did not return a clip.")
        url = urljoin(SPACE_URL, payload[0].get("url") or "")
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.netloc != SPACE_HOST or not parsed.path.startswith("/gradio_api/file="):
            raise RuntimeError("The public video model returned an unexpected file address.")

        clip = bytearray()
        with session.get(url, stream=True, timeout=(10, 25), allow_redirects=False) as video:
            if video.status_code != 200:
                raise RuntimeError("Could not download the generated video clip.")
            for chunk in video.iter_content(65536):
                clip.extend(chunk)
                if len(clip) > MAX_CLIP_BYTES:
                    raise RuntimeError("The background clip is too large.")
        if not clip:
            raise RuntimeError("The generated video clip is empty.")
        return bytes(clip)
