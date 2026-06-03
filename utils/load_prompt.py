from utils.config_loader import CONFIG


def read_prompt(prompt_path: str):
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt_content = f.read()
    return prompt_content
