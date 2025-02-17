import base64
import io
import json
import os
import re
from functools import cache

from litellm import completion
from pydantic import BaseModel

try:
    from dotenv import load_dotenv

    load_dotenv()
except:
    pass

generation_config = {
    "temperature": 0.9,  # Temperature of the sampling distribution
    "top_p": 1,  # Probability of sampling from the top p tokens
    "top_k": 1,  # Number of top tokens to sample from
    "max_output_tokens": 2048,
}


class TextEdits(BaseModel):
    term: str
    start_char: int
    end_char: int
    type: str
    fix: str
    reason: str

class SuggestedEdits(BaseModel):
    edits: list[TextEdits]


safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
]

gemini_models = [
    {
        "name": "Gemini 2.0 Flash",
        "model": "gemini/gemini-2.0-flash",
        "image_support": True,
    },
    {
        "name": "Gemini 1.5 Pro",
        "model": "gemini/gemini-1.5-pro",
        "image_support": False,
    },
]

models_dict = {model["name"]: model for model in gemini_models}


@cache
def get_file(relative_path: str) -> str:
    current_path = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(current_path, relative_path)
    with open(full_path) as f:
        return f.read()


def html_title(title: str) -> str:
    return f"<h1>{title}</h1>"


def apply_review(text: str, review: list[dict]) -> str:
    output = ""
    review = sorted(review, key=lambda x: x["start_char"])
    last_end = 0
    for entity in review:
        starts = [
            m.start() + last_end
            for m in re.finditer(entity["term"].lower(), text[last_end:].lower())
        ]
        if len(starts) > 0:
            start = starts[0]
            end = start + len(entity["term"])
            output += text[last_end:start]
            if "fix" not in entity:
                entity["fix"] = ""
            if len(entity["fix"]) > 0:
                output += get_file("templates/correction.html").format(
                    term=text[start:end], fix=entity["fix"], kind=entity["type"]
                )
            else:
                output += get_file("templates/deletion.html").format(
                    term=text[start:end], kind=entity["type"]
                )
            last_end = end
    output += text[last_end:]
    return f"<pre style='white-space: pre-wrap;'>{output}</pre>"


def review_table_summary(review: list[dict]) -> str:
    table = "<table><tr><th>Term</th><th>Fix</th><th>Type</th><th>Reason</th></tr>"
    for entity in review:
        table += f"<tr><td>{entity['term']}</td><td>{entity['fix']}</td><td>{entity['type']}</td><td>{entity.get('reason', '-')}</td></tr>"
    table += "</table>"
    return table


def review_text(model: str, text: str) -> list[dict]:
    template = get_file("templates/prompt_v1.txt")
    try:
        response = completion(
            model=model,
            messages=[{"role": "user", "content": template.format(text=text)}],
            response_format=SuggestedEdits,
        )
    except Exception as e:
        print(e)
        raise ValueError(
            f"Error while getting answer from the model, make sure the content isn't offensive or dangerous."
        )
    return json.loads(response.choices[0].message.content)["edits"]


def process_text(model: str, text: str) -> str:
    review = review_text(models_dict[model]["model"], text)
    if len(review) == 0:
        return html_title("No issues found in the text 🎉🎉🎉")
    return (
        html_title("Reviewed text")
        + apply_review(text, review)
        + html_title("Explanation")
        + review_table_summary(review)
    )

def image_to_base64_string(img):
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

def process_image(model: str, image) -> list[dict]:
    prompt = get_file("templates/prompt_image_v1.txt")
    try:
        response = completion(
            model=models_dict[model]["model"],
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": "data:image/jpeg;base64," + image_to_base64_string(image),
                        },
                    ],
                }
            ],
        )
    except ValueError as e:
        print(e)
        message = f"Error while getting answer from the model, make sure the content isn't offensive or dangerous. Please try again or change the prompt. {str(e)}"
        raise ValueError(message)
    return response.choices[0].message.content
