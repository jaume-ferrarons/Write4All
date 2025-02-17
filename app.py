import re
import gradio as gr

from review import process_text, process_image, get_file


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


text_ui = gr.Interface(
    fn=process_text,
    inputs=[
        gr.Dropdown(
            ["Gemini 2.0 Flash", "Gemini 1.5 Pro"],
            label="Model",
            value="Gemini 2.0 Flash",
            scale=1,
        ),
        gr.Textbox(lines=5, label="Text", scale=4),
    ],
    outputs=[gr.HTML(label="Revision")],
    examples=[
        ["Gemini 2.0 Flash", "The whitelist is incomplete."],
        ["Gemini 2.0 Flash", "There's not enough manpower to deliver the project"],
        ["Gemini 2.0 Flash", "This has never happened in the history of mankind!"],
        ["Gemini 2.0 Flash", "El hombre desciende del mono."],
        ["Gemini 2.0 Flash", "Els homes són animals"],
    ],
)

image_ui = gr.Interface(
    fn=process_image,
    inputs=[
        gr.Dropdown(
            ["Gemini 2.0 Flash"],
            label="Model",
            value="Gemini 2.0 Flash",
            scale=1,
        ),
        gr.Image(sources=["upload", "clipboard"], type="pil"),
    ],
    outputs=["markdown"],
    examples=[
        ["Gemini 2.0 Flash", "static/images/CEOs.png"],
        ["Gemini 2.0 Flash", "static/images/meat_grid.png"],
        ["Gemini 2.0 Flash", "static/images/elephants.jpg"],
        ["Gemini 2.0 Flash", "static/images/crosses.jpg"],
    ],
)

with gr.Blocks() as demo:
    gr.Markdown(get_file("static/intro.md"))
    gr.TabbedInterface([text_ui, image_ui], ["Check texts", "Check images"])

if __name__ == "__main__":
    demo.launch()
