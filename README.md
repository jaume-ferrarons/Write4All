---
title: Write4All
emoji: ✍️✅
colorFrom: pink
colorTo: green
sdk: gradio
sdk_version: 5.16.0
app_file: app.py
pinned: true
license: mit 
---

# ✅Write4All

In a world where diversity and inclusivity are essential, crafting content that resonates with everyone can be a challenge. With ✅Write4All I hope making the world more inclusive, one word and image at a time.

See it in action in:
- HuggingFace Spaces: [✅Write4All](https://huggingface.co/spaces/Jaume/Write4All).
- Examples notebook: [✅Write4All Examples](./notebooks/examples.ipynb).

## Requirements

- Python 3.12+
- uv
- Gemini API key


## Installation

```bash
uv sync --frozen
```

## Running the app

```bash
export GEMINI_API_KEY=your_api_key_here
uv run gradio app.py
```

## Development
HuggingFace Spaces require the `requirements.txt` file to be updated with the latest dependencies.
Update the `requirements.txt` file with the following command:
```bash
uv export --no-dev --format requirements-txt > requirements.txt
```
