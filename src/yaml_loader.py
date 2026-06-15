from pathlib import Path

import yaml


class YamlLoaderError(Exception):
    """Raised when YAML input cannot be loaded safely."""


def load_yaml_file(path):
    """Read a YAML file and return its root dictionary."""
    yaml_path = Path(path)
    if not yaml_path.exists():
        raise YamlLoaderError(f"Input YAML file does not exist: {yaml_path}")
    if not yaml_path.is_file():
        raise YamlLoaderError(f"Input path is not a file: {yaml_path}")

    try:
        text = yaml_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise YamlLoaderError(f"Unable to read input YAML file: {exc}") from exc

    if not text.strip():
        raise YamlLoaderError("Input YAML file is empty.")

    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise YamlLoaderError(f"Invalid YAML syntax: {exc}") from exc

    if data is None:
        raise YamlLoaderError("Input YAML file is empty.")
    if not isinstance(data, dict):
        raise YamlLoaderError("YAML root must be a dictionary/object.")
    return data
