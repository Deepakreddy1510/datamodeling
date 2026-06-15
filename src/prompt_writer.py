import json
from pathlib import Path


class PromptWriterError(Exception):
    """Raised when prompt templates cannot be rendered."""


def pretty_json(value):
    return json.dumps(value, indent=2, sort_keys=True)


def read_template(template_path):
    path = Path(template_path)
    if not path.exists():
        raise PromptWriterError(f"Prompt template does not exist: {path}")
    return path.read_text(encoding="utf-8")


def render_template(template_text, replacements):
    rendered = template_text
    for placeholder, value in replacements.items():
        token = "{{" + placeholder + "}}"
        if token not in rendered:
            raise PromptWriterError(f"Required placeholder is missing from template: {token}")
        rendered = rendered.replace(token, value)

    if "{{" in rendered or "}}" in rendered:
        raise PromptWriterError("Template contains unreplaced placeholders.")
    return rendered


def write_prompt(template_path, output_path, replacements):
    template_text = read_template(template_path)
    rendered = render_template(template_text, replacements)
    Path(output_path).write_text(rendered, encoding="utf-8")
    return rendered
