from utils.config_loader import CONFIG


def read_prompt(prompt_path: str = CONFIG["prompt_path"]):
    with open(prompt_path) as f:
        prompt_content = f.read()
    return prompt_content


if __name__ == "__main__":
    print(read_prompt())
