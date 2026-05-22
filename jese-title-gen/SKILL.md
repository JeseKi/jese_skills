---
name: jese-title-gen
description: Generate high-click WeChat public account titles from article content using a configured LLM. Use when the user asks for 爆款标题, 公众号标题, title generation, or clickable headline candidates; the bundled script reads LLM credentials from .env or environment variables so the agent never needs to see API tokens.
---

# Jese Title Gen

Use this skill to generate non-structured title suggestions from article content with the bundled script.

## Workflow

1. Save or identify the article content file.
2. Choose parameters only when the user asks or the context makes them obvious:
   - `--num` for the required number of titles
   - `--model`, default `gemini-3.5-flash`
   - `--base-url`, default from `JESE_LLM_API_BASE_URL`
   - `--api-key`, default from `JESE_LLM_API_KEY`
3. Run the script from the repository root:

```bash
python jese-title-gen/scripts/generate_titles.py \
  --num 8 \
  --content-file ./article.md
```

4. The script prints the final generated text to stdout. Report that text to the user.

## Credentials

Do not ask the user for API tokens and do not read or print `.env` contents.

The script loads `.env` files itself and reads:

- `JESE_LLM_API_BASE_URL` (required unless `--base-url` is provided)
- `JESE_LLM_API_KEY` (required unless `--api-key` is provided)

`.env` lookup order:

1. current working directory `.env`
2. `~/.jese_skills/.env`

## Examples

Generate 8 titles:

```bash
python jese-title-gen/scripts/generate_titles.py \
  --num 8 \
  --content-file ./article.md
```

Use a different model:

```bash
python jese-title-gen/scripts/generate_titles.py \
  --model gemini-3.5-flash \
  --num 5 \
  --content-file ./article.md
```
