import re
import os
import gradio as gr
import json
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

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

text_model = genai.GenerativeModel(
    model_name="gemini-1.0-pro",
    generation_config=generation_config,
    safety_settings=safety_settings,
)
vision_model = genai.GenerativeModel(
    "gemini-pro-vision",
    generation_config=generation_config,
    safety_settings=safety_settings,
)


@cache
def get_file(path: str) -> str:
    with open(path) as f:
        return f.read()


def fix_json(json_str: str) -> str:
    template = get_file("templates/prompt_json_fix.txt")
    prompt = template.format(json=json_str)
    response = text_model.generate_content(prompt).text
    return response.split("```json")[1].split("```")[0]


def get_json_content(response: str) -> dict:
    print(response)
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


def review_text(text: str) -> list[dict]:
    template = get_file("templates/prompt_v1.txt")
    try:
        response = text_model.generate_content(template.format(text=text)).text
    except ValueError as e:
        print(e)
        raise ValueError(
            f"Error while getting answer from the model, make sure the content isn't offensive or dangerous."
        )
    return get_json_content(response)


def review_image(image) -> list[dict]:
    prompt = get_file("templates/prompt_image_v1.txt")
    try:
        response = vision_model.generate_content([prompt, image]).text
    except ValueError as e:
        print(e)
        message = "Error while getting answer from the model, make sure the content isn't offensive or dangerous. Please try again or change the prompt."
        gr.Error(message)
        raise ValueError(message)
    return response


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
    return output


def review_table_summary(review: list[dict]) -> str:
    table = "<table><tr><th>Term</th><th>Fix</th><th>Type</th><th>Reason</th></tr>"
    for entity in review:
        table += f"<tr><td>{entity['term']}</td><td>{entity['fix']}</td><td>{entity['type']}</td><td>{entity.get('reason', '-')}</td></tr>"
    table += "</table>"
    return table


def format_entities(text: str, review: list[dict]) -> list[dict]:
    entities = []
    for entity in review:
        # Find all occurrences of the term in the text
        starts = [m.start() for m in re.finditer(entity["term"], text)]
        if len(starts) > 0:
            entities.append(
                {
                    "term": entity["term"],
                    "start": starts[0],
                    "end": starts[0] + len(entity["term"]),
                    "entity": entity["type"],
                    "fix": entity["fix"],
                }
            )
        else:
            print(f"Term '{entity['term']}' not found in the text: '{text}'")
    return entities


def process_text(text):
    review = review_text(text)
    if len(review) == 0:
        return html_title("No issues found in the text 🎉🎉🎉")
    return (
        html_title("Reviewed text")
        + apply_review(text, review)
        + html_title("Explanation")
        + review_table_summary(review)
    )


def process_image(image):
    print(image)
    return review_image(image)


text_ui = gr.Interface(
    fn=process_text,
    inputs=["text"],
    outputs=[gr.HTML(label="Revision")],
    examples=[
        "The whitelist is incomplete.",
        "There's not enough manpower to deliver the project",
        "This has never happened in the history of mankind!",
        "El hombre desciende del mono.",
        "Els homes són animals",
    ],
)

image_ui = gr.Interface(
    fn=process_image,
    inputs=gr.Image(sources=["upload", "clipboard"], type="pil"),
    outputs=["markdown"],
    examples=["static/images/CEOs.png", "static/images/meat_grid.png"],
)

with gr.Blocks() as demo:
    gr.Markdown(get_file("static/intro.md"))
    gr.TabbedInterface([text_ui, image_ui], ["Check texts", "Check images"])

if __name__ == "__main__":
    demo.launch()
