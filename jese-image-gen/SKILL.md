---
name: jese-image-gen
description: Generate or transform images through the local Jese image generation API. Use when the user asks to create an image file from a prompt, optionally with aspect ratio, size, model, output path, or reference images; the bundled script reads credentials from .env or environment variables so the agent never needs to see API tokens.
---

# Jese Image Gen

Use this skill to generate an actual image file with the bundled script.

## Workflow

1. Write a clear prompt from the user's request.
2. Choose parameters only when the user asks or the context makes them obvious:
   - `--ratio`, default `1:1`
   - `--size`, default `2K`
   - `--model`, default `nano-banana-fast`
   - repeated `--input-image` for references
   - `--output` for an explicit destination
3. Run the script from the repository root:

```bash
python jese-image-gen/scripts/generate_image.py \
  --prompt "A studio product photo of a translucent blue glass vase" \
  --ratio 1:1 \
  --size 2K
```

4. The script prints the generated image path as the final stdout line. Report that path to the user.

## Credentials

Do not ask the user for API tokens and do not read or print `.env` contents.

The script loads `.env` files itself and reads:

- `JESE_IMAGE_GEN_API_TOKEN` (required)
- `JESE_IMAGE_GEN_API_BASE_URL` (optional)

`.env` lookup order:

1. current working directory `.env`
2. `~/.jese_skills/.env`

## Examples

Generate from text:

```bash
python jese-image-gen/scripts/generate_image.py \
  --prompt "A clean icon-style illustration of a bamboo steamer" \
  --ratio 1:1
```

Generate with references:

```bash
python jese-image-gen/scripts/generate_image.py \
  --prompt "Use the reference product shape, render it as a premium catalog image" \
  --ratio 4:3 \
  --input-image ./reference.png
```
