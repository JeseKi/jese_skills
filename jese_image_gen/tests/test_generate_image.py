import base64
import importlib.util
import json
from pathlib import Path

import pytest


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "generate_image.py"
)
SPEC = importlib.util.spec_from_file_location("generate_image", SCRIPT_PATH)
assert SPEC is not None
generate_image = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(generate_image)


def test_build_payload_prompt_only() -> None:
    payload = json.loads(generate_image.build_payload("make a vase", "2K", "1:1", []))

    assert payload["contents"][0]["parts"] == [{"text": "make a vase"}]
    assert payload["generationConfig"]["imageConfig"] == {
        "aspectRatio": "1:1",
        "imageSize": "2K",
    }


def test_build_payload_with_multiple_input_images(tmp_path: Path) -> None:
    png = tmp_path / "one.png"
    jpg = tmp_path / "two.jpg"
    png.write_bytes(b"png-bytes")
    jpg.write_bytes(b"jpg-bytes")

    payload = json.loads(
        generate_image.build_payload("use these references", "1K", "16:9", [str(png), str(jpg)])
    )

    parts = payload["contents"][0]["parts"]
    assert parts[0]["inline_data"]["mime_type"] == "image/png"
    assert parts[0]["inline_data"]["data"] == base64.b64encode(b"png-bytes").decode()
    assert parts[1]["inline_data"]["mime_type"] == "image/jpeg"
    assert parts[1]["inline_data"]["data"] == base64.b64encode(b"jpg-bytes").decode()
    assert parts[2] == {"text": "use these references"}


def test_parse_dotenv_line() -> None:
    assert generate_image.parse_dotenv_line("TOKEN=value") == ("TOKEN", "value")
    assert generate_image.parse_dotenv_line("TOKEN='quoted value'") == (
        "TOKEN",
        "quoted value",
    )
    assert generate_image.parse_dotenv_line('TOKEN="quoted value"') == (
        "TOKEN",
        "quoted value",
    )
    assert generate_image.parse_dotenv_line("# comment") is None
    assert generate_image.parse_dotenv_line("") is None


def test_dotenv_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)

    assert generate_image.dotenv_paths() == [
        tmp_path / ".env",
        Path.home() / ".jese_skills" / ".env",
    ]


def test_load_dotenv_does_not_overwrite_existing_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "JESE_IMAGE_GEN_API_TOKEN=from-file\n"
        "JESE_IMAGE_GEN_API_BASE_URL='https://example.test'\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("JESE_IMAGE_GEN_API_TOKEN", "from-env")
    monkeypatch.delenv("JESE_IMAGE_GEN_API_BASE_URL", raising=False)
    monkeypatch.setattr(generate_image, "dotenv_paths", lambda: [env_file])

    generate_image.load_dotenv()

    assert generate_image.os.environ["JESE_IMAGE_GEN_API_TOKEN"] == "from-env"
    assert generate_image.os.environ["JESE_IMAGE_GEN_API_BASE_URL"] == "https://example.test"


def test_extract_png_bytes_supports_inline_data_styles() -> None:
    image_bytes = b"image-bytes"
    encoded = base64.b64encode(image_bytes).decode()

    assert (
        generate_image.extract_png_bytes(
            {"candidates": [{"content": {"parts": [{"inlineData": {"data": encoded}}]}}]}
        )
        == image_bytes
    )
    assert (
        generate_image.extract_png_bytes(
            {"candidates": [{"content": {"parts": [{"inline_data": {"data": encoded}}]}}]}
        )
        == image_bytes
    )


def test_extract_png_bytes_missing_image_data() -> None:
    with pytest.raises(ValueError, match="inline image data"):
        generate_image.extract_png_bytes({"candidates": [{"content": {"parts": [{"text": "no"}]}}]})
