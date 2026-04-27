#!/usr/bin/env python3
import argparse
import base64
import json
import mimetypes
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests


DEFAULT_API_BASE_URL = "https://ki-llmapi.kispace.cc/v1beta/models"
TOKEN_ENV_VAR = "JESE_IMAGE_GEN_API_TOKEN"
API_BASE_URL_ENV_VAR = "JESE_IMAGE_GEN_API_BASE_URL"
SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = SKILL_ROOT / "outputs"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Call the Jese image generation API and save the returned image."
    )
    parser.add_argument(
        "--model",
        choices=["nano-banana-fast", "nano-banana-pro"],
        default="nano-banana-fast",
        help="Model name. Defaults to nano-banana-fast.",
    )
    parser.add_argument("--prompt", required=True, help="Prompt text to send.")
    parser.add_argument("--size", default="2K", help="Image size, e.g. 1K, 2K.")
    parser.add_argument("--ratio", default="1:1", help="Aspect ratio, e.g. 1:1, 16:9.")
    parser.add_argument(
        "--input-image",
        action="append",
        default=[],
        help=(
            "Optional input image path. Can be provided multiple times, e.g. "
            "--input-image ref1.png --input-image ref2.jpg."
        ),
    )
    parser.add_argument(
        "--output",
        default=None,
        help=(
            "Output image path. Defaults to a timestamped PNG under "
            "jese_image_gen/outputs/."
        ),
    )
    parser.add_argument(
        "--connect-timeout",
        type=int,
        default=300,
        help="Connection timeout in seconds. Defaults to 300.",
    )
    parser.add_argument(
        "--max-time",
        type=int,
        default=600,
        help="Maximum total request time in seconds. Defaults to 600.",
    )
    parser.add_argument(
        "--response-json",
        default=None,
        help="Optional path to save the raw JSON response for debugging.",
    )
    return parser.parse_args()


def dotenv_paths() -> list[Path]:
    candidates = [
        Path.cwd() / ".env",
        Path.home() / ".jese_skills" / ".env",
    ]
    unique_paths: list[Path] = []
    for path in candidates:
        if path not in unique_paths:
            unique_paths.append(path)
    return unique_paths


def parse_dotenv_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None

    key, value = stripped.split("=", 1)
    key = key.strip()
    value = value.strip()
    if not key:
        return None

    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]

    return key, value


def load_dotenv() -> None:
    for path in dotenv_paths():
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            parsed = parse_dotenv_line(line)
            if parsed is None:
                continue
            key, value = parsed
            os.environ.setdefault(key, value)


def default_output_path() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return DEFAULT_OUTPUT_DIR / f"jese_image_{timestamp}.png"


def encode_image_file(image_path: str) -> dict[str, dict[str, str]]:
    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(f"Input image not found: {image_path}")

    mime_type, _ = mimetypes.guess_type(path.name)
    if not mime_type or not mime_type.startswith("image/"):
        mime_type = "image/png"

    data = base64.b64encode(path.read_bytes()).decode("utf-8")
    return {
        "inline_data": {
            "mime_type": mime_type,
            "data": data,
        }
    }


def build_payload(prompt: str, size: str, ratio: str, input_images: list[str]) -> bytes:
    parts: list[dict[str, Any]] = []

    for image_path in input_images:
        parts.append(encode_image_file(image_path))

    parts.append({"text": prompt})

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": parts,
            }
        ],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
            "imageConfig": {
                "aspectRatio": ratio,
                "imageSize": size,
            },
        },
    }
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def extract_png_bytes(data: dict[str, Any]) -> bytes:
    try:
        parts = data["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("Response does not contain candidate content") from exc

    for part in parts:
        inline_data = part.get("inlineData") or part.get("inline_data")
        if not inline_data:
            continue
        b64_data = inline_data.get("data")
        if b64_data:
            return base64.b64decode(b64_data)

    raise ValueError("Response does not contain inline image data")


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def save_image(path: Path, image_bytes: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(image_bytes)


def main() -> int:
    args = parse_args()
    load_dotenv()

    token = os.environ.get(TOKEN_ENV_VAR)
    if not token:
        print(f"Missing required environment variable: {TOKEN_ENV_VAR}", file=sys.stderr)
        return 1

    api_base_url = os.environ.get(API_BASE_URL_ENV_VAR, DEFAULT_API_BASE_URL).rstrip("/")
    api_url = f"{api_base_url}/{args.model}:generateContent"
    output_path = Path(args.output) if args.output else default_output_path()

    deadline = time.monotonic() + args.max_time

    try:
        response = requests.post(
            api_url,
            data=build_payload(args.prompt, args.size, args.ratio, args.input_image),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=(args.connect_timeout, args.max_time),
            stream=True,
        )
        response.raise_for_status()
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except requests.Timeout as exc:
        print(f"Request timed out: {exc}", file=sys.stderr)
        return 1
    except requests.RequestException as exc:
        print(f"Request failed: {exc}", file=sys.stderr)
        return 1

    raw = bytearray()
    try:
        for chunk in response.iter_content(chunk_size=65536):
            if not chunk:
                continue
            if time.monotonic() > deadline:
                print(
                    f"Request exceeded max-time of {args.max_time} seconds",
                    file=sys.stderr,
                )
                return 1
            raw.extend(chunk)
    finally:
        response.close()

    try:
        response_json = json.loads(bytes(raw).decode("utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Failed to parse JSON response: {exc}", file=sys.stderr)
        return 1

    if args.response_json:
        save_json(Path(args.response_json), response_json)

    try:
        image_bytes = extract_png_bytes(response_json)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    save_image(output_path, image_bytes)

    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
