import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "generate_titles.py"
)
SPEC = importlib.util.spec_from_file_location("generate_titles", SCRIPT_PATH)
assert SPEC is not None
generate_titles = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(generate_titles)


def test_build_user_prompt_injects_content_and_num() -> None:
    prompt = generate_titles.build_user_prompt("文章正文", 6)

    assert '"""\n文章正文\n\n"""' in prompt
    assert "给我来 6 个标题" in prompt
    assert "给我来 num 个标题" not in prompt


def test_build_messages_wraps_prompt() -> None:
    messages = generate_titles.build_messages("content", 3)

    assert messages == [
        {
            "role": "user",
            "content": generate_titles.build_user_prompt("content", 3),
        }
    ]


def test_parse_dotenv_line() -> None:
    assert generate_titles.parse_dotenv_line("TOKEN=value") == ("TOKEN", "value")
    assert generate_titles.parse_dotenv_line("TOKEN='quoted value'") == (
        "TOKEN",
        "quoted value",
    )
    assert generate_titles.parse_dotenv_line('TOKEN="quoted value"') == (
        "TOKEN",
        "quoted value",
    )
    assert generate_titles.parse_dotenv_line("# comment") is None
    assert generate_titles.parse_dotenv_line("") is None


def test_dotenv_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)

    assert generate_titles.dotenv_paths() == [
        tmp_path / ".env",
        Path.home() / ".jese_skills" / ".env",
    ]


def test_load_dotenv_does_not_overwrite_existing_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "JESE_LLM_API_KEY=from-file\n"
        "JESE_LLM_API_BASE_URL='https://example.test'\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("JESE_LLM_API_KEY", "from-env")
    monkeypatch.delenv("JESE_LLM_API_BASE_URL", raising=False)
    monkeypatch.setattr(generate_titles, "dotenv_paths", lambda: [env_file])

    generate_titles.load_dotenv()

    assert generate_titles.os.environ["JESE_LLM_API_KEY"] == "from-env"
    assert generate_titles.os.environ["JESE_LLM_API_BASE_URL"] == "https://example.test"


def test_read_content_file(tmp_path: Path) -> None:
    content_file = tmp_path / "article.md"
    content_file.write_text("hello", encoding="utf-8")

    assert generate_titles.read_content_file(str(content_file)) == "hello"


def test_extract_stream_text() -> None:
    chunks = [
        SimpleNamespace(
            choices=[SimpleNamespace(delta=SimpleNamespace(content="one"))]
        ),
        SimpleNamespace(choices=[]),
        SimpleNamespace(
            choices=[SimpleNamespace(delta=SimpleNamespace(content=" two"))]
        ),
        SimpleNamespace(
            choices=[SimpleNamespace(delta=SimpleNamespace(content=None))]
        ),
    ]

    assert generate_titles.extract_stream_text(chunks) == "one two"
