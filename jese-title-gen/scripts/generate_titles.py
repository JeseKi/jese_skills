#!/usr/bin/env python3
import argparse
import os
import sys
from pathlib import Path
from typing import Any

from openai import OpenAI, OpenAIError
from openai.types.chat import ChatCompletionMessageParam


DEFAULT_MODEL = "gemini-3.5-flash"
API_BASE_URL_ENV_VAR = "JESE_LLM_API_BASE_URL"
API_KEY_ENV_VAR = "JESE_LLM_API_KEY"

PROMPT_TEMPLATE = '''{{ 
爆款公众号标题生成大师 (Skill Prompt)
【角色设定】
你是一位深谙人性与流量密码的资深新媒体主编。你极度擅长拆解爆款逻辑，能够精准操盘流量，同时熟练拿捏“极致吸睛”与“平台合规”之间的微妙平衡。你的目标是为输入的主题创作出让人无法拒绝点击的公众号标题。
【核心创作原则】
-
强冲突与反直觉： 打破常规认知，把两个看似不相关甚至对立的元素放在一起，制造强烈的反差感，瞬间拉满读者的好奇心。
-
极致大白话： 拒绝故作高深。用最接地气、最生活化的语言直击痛点，确保读者在一秒内看懂并产生代入感。
-
情绪价值拉满： 标题必须是情绪的放大器。精准捕捉焦虑、猎奇、愤怒、爽感或共鸣，让标题本身成为一种情绪释放。
-
短平快与音律美： 极度克制字数，砍掉所有废话。追求句式的对称或内在的节奏感，读起来必须朗朗上口。但要足够简洁、清晰、有力，不能让读者看了感觉摸不着头脑。
【边界与尺度把控】
-
犀利且带感： 观点必须一针见血，可以带有适度的“冒犯感”或让人心跳加速的“擦边”刺激感，以榨取最大流量。
-
底线不可破： 在疯狂试探流量天花板的同时，必须自带“合规雷达”，巧妙规避平台违禁词与低俗红线，做到既野又稳。
【执行工作流】
1. 精准切脉： 收到主题后，立刻提取出受众最在意的核心利益点（如：搞钱、省力、魅力提升、情绪安抚等）。
1. 角度爆破： 结合上述“核心创作原则”，从多个角度（如：揭秘捷径、痛点放大、反常识陈述）构思初稿。
2. 精修打磨： 对初稿进行字词级的删减与替换，优化音律，强化冲突。
3. 合规自检： 审视标题的“犀利度”是否安全着陆。 【输出要求】 每次接到任务，请直接输出 5-8 个不同维度的候选标题，并在每个标题后用一句话简述其所使用的“爆款逻辑”（例如：冲突点在哪里、调动了什么情绪）。 *** 你可以保存这个模板，下次需要起标题的时候，直接把这段要求发出来，再附上你具体的文章内容或主题，就能快速得到符合你风格的标题矩阵了。}}

"""
{content}

"""

给我来 {num} 个标题'''


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate high-click title candidates from article content."
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help=f"OpenAI-compatible API base URL. Defaults to {API_BASE_URL_ENV_VAR}.",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help=f"OpenAI-compatible API key. Defaults to {API_KEY_ENV_VAR}.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Model name. Defaults to {DEFAULT_MODEL}.",
    )
    parser.add_argument(
        "--num",
        type=int,
        required=True,
        help="Number of titles to generate.",
    )
    parser.add_argument(
        "--content-file",
        required=True,
        help="Path to the article content file.",
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


def build_user_prompt(content: str, num: int) -> str:
    return PROMPT_TEMPLATE.format(content=content, num=num)


def build_messages(content: str, num: int) -> list[ChatCompletionMessageParam]:
    message: ChatCompletionMessageParam = {
        "role": "user",
        "content": build_user_prompt(content, num),
    }
    return [message]


def read_content_file(content_file: str) -> str:
    path = Path(content_file)
    if not path.is_file():
        raise FileNotFoundError(f"Content file not found: {content_file}")
    return path.read_text(encoding="utf-8")


def extract_stream_text(chunks: Any) -> str:
    parts: list[str] = []
    for chunk in chunks:
        choices = getattr(chunk, "choices", None)
        if not choices:
            continue
        delta = getattr(choices[0], "delta", None)
        content = getattr(delta, "content", None)
        if isinstance(content, str):
            parts.append(content)
    return "".join(parts)


def generate_titles(
    *,
    base_url: str,
    api_key: str,
    model: str,
    content: str,
    num: int,
) -> str:
    client = OpenAI(base_url=base_url, api_key=api_key)
    chunks = client.chat.completions.create(
        model=model,
        messages=build_messages(content, num),
        stream=True,
        extra_body={"group": "default"},
    )
    return extract_stream_text(chunks)


def main() -> int:
    args = parse_args()
    load_dotenv()

    if args.num <= 0:
        print("--num must be greater than 0", file=sys.stderr)
        return 1

    base_url = args.base_url or os.environ.get(API_BASE_URL_ENV_VAR)
    if not base_url:
        print(
            f"Missing required environment variable or argument: {API_BASE_URL_ENV_VAR}",
            file=sys.stderr,
        )
        return 1

    api_key = args.api_key or os.environ.get(API_KEY_ENV_VAR)
    if not api_key:
        print(
            f"Missing required environment variable or argument: {API_KEY_ENV_VAR}",
            file=sys.stderr,
        )
        return 1

    try:
        content = read_content_file(args.content_file)
        result = generate_titles(
            base_url=base_url,
            api_key=api_key,
            model=args.model,
            content=content,
            num=args.num,
        )
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except OpenAIError as exc:
        print(f"Request failed: {exc}", file=sys.stderr)
        return 1

    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
