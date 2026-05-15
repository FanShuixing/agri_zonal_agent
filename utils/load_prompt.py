from utils.config_loader import CONFIG


def read_prompt(prompt_path: str):
    with open(prompt_path) as f:
        prompt_content = f.read()
    return prompt_content
