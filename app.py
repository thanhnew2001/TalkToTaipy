from taipy.gui import Gui, notify

import random
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

context_data = pd.read_csv(CONTEXT_PATH, sep=";")
data = pd.read_csv(SAMPLE_PATH, sep=",", encoding="ISO-8859-1")

data["ORDERDATE"] = pd.to_datetime(data["ORDERDATE"])
data = data.sort_values(by="ORDERDATE")
data_columns = data.columns.tolist()

transformed_data = data.copy()

context = ""
for instruction, code in zip(context_data["instruction"], context_data["code"]):
    context += f"{instruction}\n{code}\n"

context_columns = ["Sales", "Revenue", "Date", "Usage", "Energy"]
# Replace occurences of the context_columns in context by _
for column in context_columns:
    context = context.replace(column, "_")

# For all occurences of _ in context, replace it by a random column from data_columns
for _ in range(context.count("_")):
    context = context.replace("_", random.choice(data_columns), 1)


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


def plot_prompt(input_instruction: str) -> str:
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
        print(output)
        timeout += 1
        final_result += output

    output_code = f"""<{final_result.split("<")[1].split(">")[0]}>"""
    return output_code


def plot(state) -> None:
    """
    Prompt StarCoder to generate Taipy GUI code when user presses enter

    Args:
        state (State): Taipy GUI state
    """
    state.result = plot_prompt(state.plot_instruction)
    state.p.update_content(state, state.result)
    notify(state, "success", "App Updated!")
    print(f"Plot code: {state.result}")


def modify_data(state) -> None:
    """
    Prompts StarCoder to generate pandas code to transform data

    Args:
        state (State): Taipy GUI state
    """
    data_prompt = f"def transfom(data: pd.DataFrame) -> pd.DataFrame:\n  # {state.data_instruction}\n  return "
    output = query(
        {
            "inputs": data_prompt,
            "parameters": {
                "return_full_text": False,
            },
        }
    )[0]["generated_text"]
    output = output.split("\n")[0]
    print(f"Data transformation code: {output}")
    state.transformed_data = pd.DataFrame(eval(output))


def reset_data(state) -> None:
    """
    Resets transformed data to original data

    Args:
        state (State): Taipy GUI state
    """
    state.transformed_data = state.data.copy()


data_instruction = ""
plot_instruction = ""
result = ""


page = """
# Taipy**Copilot**{: .color-primary}

<|Original Data|expandable|expanded=False|
<|{data}|table|width=100%|page_size=5|>
|>

Enter your instruction to **modify**{: .color-primary} data here:
<|{data_instruction}|input|on_action=modify_data|class_name=fullwidth|change_delay=1000|>

<|Transformed Data|expandable|expanded=False|
<|{transformed_data}|table|width=100%|page_size=5|>
|>

<|Reset Transformed Data|button|on_action=reset_data|>

Enter your instruction to **plot**{: .color-primary} data here:
<|{plot_instruction}|input|on_action=plot|class_name=fullwidth|change_delay=1000|>

<|part|partial={p}|>
"""

gui = Gui(page)
p = gui.add_partial("""""")
gui.run(port=6969)
