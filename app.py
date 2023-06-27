from taipy.gui import Gui, notify

import pandas as pd
import requests

SECRET_PATH = "secret.txt"
with open(SECRET_PATH, "r") as f:
    API_TOKEN = f.read()


API_URL = "https://api-inference.huggingface.co/models/bigcode/starcoder"
headers = {"Authorization": f"Bearer {API_TOKEN}"}

DATA_PATH = "data.csv"

CONTEXT_PATH = "context_data.csv"
SAMPLE_PATH = "sales_data_sample.csv"

df = pd.read_csv(CONTEXT_PATH, sep=";")
data = pd.read_csv(SAMPLE_PATH, sep=",", encoding="ISO-8859-1")

context = ""
for instruction, code in zip(df["instruction"], df["code"]):
    context += f"{instruction}\n{code}\n"


def query(payload: dict) -> dict:
    """
    Queries StarCoder API

    Args:
        payload: Payload for StarCoder API

    Returns:
        dict: StarCoder API response
    """
    response = requests.post(API_URL, headers=headers, json=payload, timeout=20)
    return response.json()


def prompt(input_instruction: str) -> str:
    """
    Prompts StarCoder to generate Taipy GUI code

    Args:
        instuction (str): Instruction for StarCoder

    Returns:
        str: Taipy GUI code
    """
    current_prompt = f"{context}\n{input_instruction}\n"
    output = ""
    final_result = ""

    # Re-query until the output contains the closing tag
    timeout = 0
    while ">" not in output and timeout < 10:
        output = query(
            {
                "inputs": current_prompt + output,
                "parameters": {
                    "return_full_text": False,
                },
            }
        )[0]["generated_text"]
        timeout += 1
        final_result += output

    output_code = f"""<{final_result.split("<")[1].split(">")[0]}>"""
    return output_code


def on_enter_press(state) -> None:
    """
    Prompt StarCoder to generate Taipy GUI code when user presses enter

    Args:
        state (State): Taipy GUI state
    """
    state.result = prompt(state.instruction)
    state.p.update_content(state, state.result)
    notify(state, "success", "App Updated!")
    print(state.result)


instruction = ""
result = ""


page = """
# Taipy**Copilot**{: .color-primary}

Enter your instruction here:
<|{instruction}|input|on_action=on_enter_press|class_name=fullwidth|change_delay=500|>

<|Data|expandable|expanded=False|
<|{data}|table|width=100%|page_size=5|>
|>

<|part|partial={p}|>
"""

gui = Gui(page)
p = gui.add_partial("""""")
gui.run(port=6969)
