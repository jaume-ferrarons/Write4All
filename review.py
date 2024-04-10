import json
import os
import re
from functools import cache

import google.generativeai as genai

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

safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
]


gemini_1_0 = genai.GenerativeModel(
    model_name="gemini-1.0-pro",
    generation_config=generation_config,
    safety_settings=safety_settings,
)
gemini_1_5 = genai.GenerativeModel(
    model_name="gemini-1.5-pro-latest",
    generation_config=generation_config,
    safety_settings=safety_settings,
)
gemini_1_0_vision = genai.GenerativeModel(
    "gemini-pro-vision",
    generation_config=generation_config,
    safety_settings=safety_settings,
)


genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

@cache
def get_file(relative_path: str) -> str:
    current_path = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(current_path, relative_path)
    with open(full_path) as f:
        return f.read()
    
def fix_json(json_str: str) -> str:
    template = get_file("templates/prompt_json_fix.txt")
    prompt = template.format(json=json_str)
    response = gemini_1_0.generate_content(prompt).text
    return response.split("```json")[1].split("```")[0]


def get_json_content(response: str) -> dict:
    if "```json" not in response:
        return []
    raw_json = response.split("```json")[1].split("```")[0]
    try:
        return json.loads(raw_json)
    except json.JSONDecodeError as e:
        print(e)
        new_json = fix_json(raw_json)
        print(new_json)
        return json.loads(new_json)


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
            output += get_file("templates/correction.html").format(
                term=text[start:end], fix=entity["fix"], kind=entity["type"]
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

def review_text(text: str, text_model: genai.GenerativeModel) -> list[dict]:
    template = get_file("templates/prompt_v1.txt")
    try:
        response = text_model.generate_content(template.format(text=text)).text
    except ValueError as e:
        print(e)
        raise ValueError(
            f"Error while getting answer from the model, make sure the content isn't offensive or dangerous."
        )
    return get_json_content(response)

def process_text(model: str, text: str) -> str:
    text_model = gemini_1_0 if model == "Gemini 1.0 Pro" else gemini_1_5
    review = review_text(text, text_model)
    if len(review) == 0:
        return html_title("No issues found in the text 🎉🎉🎉")
    return (
        html_title("Reviewed text")
        + apply_review(text, review)
        + html_title("Explanation")
        + review_table_summary(review)
    )


def review_image(image, vision_model: genai.GenerativeModel) -> list[dict]:
    prompt = get_file("templates/prompt_image_v1.txt")
    try:
        response = vision_model.generate_content([prompt, image]).text
    except ValueError as e:
        print(e)
        message = f"Error while getting answer from the model, make sure the content isn't offensive or dangerous. Please try again or change the prompt. {str(e)}"
        raise ValueError(message)
    return response


def process_image(model: str, image):
    vision_model = gemini_1_0_vision if model == "Gemini 1.0 Pro Vision" else gemini_1_5
    return review_image(image, vision_model)