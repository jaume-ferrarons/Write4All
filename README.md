---
title: Write4All
emoji: ✍️✅
colorFrom: pink
colorTo: green
sdk: gradio
sdk_version: 4.25.0
app_file: app.py
pinned: true
license: mit 
---

Check out the configuration reference at https://huggingface.co/docs/hub/spaces-config-reference


## Running the app

```bash
poetry install
poetry run gradio app.py
```

Update the requirements.txt file with the following command:
```bash
poetry export --without-hashes --without dev -f requirements.txt -o requirements.txt
```