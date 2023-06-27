from taipy.gui import Gui, notify

import random
import re
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

transformed_data = data.copy()

data_columns = data.columns.tolist()
context_columns = ["Sales", "Revenue", "Date", "Usage", "Energy"]

context = ""
for instruction, code in zip(context_data["instruction"], context_data["code"]):
    example = f"{instruction}\n{code}\n"
    # Replace context column names with data column names
    for column in context_columns:
        example = example.replace(column, random.choice(data_columns))
    context += example


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
        timeout += 1
        final_result += output

    output_code = f"""<{final_result.split("<")[1].split(">")[0]}>"""
    pattern = r"<.*\|chart\|.*>"
    if bool(re.search(pattern, output_code)):
        return output_code
    else:
        raise Exception("Generated code is incorrect")


def plot(state) -> None:
    """
    Prompt StarCoder to generate Taipy GUI code when user presses enter

    Args:
        state (State): Taipy GUI state
    """
    state.result = plot_prompt(state.plot_instruction)
    state.p.update_content(state, state.result)
    notify(state, "success", "Plot Updated!")
    print(f"Plot code: {state.result}")


def on_exception(state, function_name: str, ex: Exception):
    notify(state, "error", f"An error occured in {function_name}: {ex}")


def modify_data(state) -> None:
    """
    Prompts StarCoder to generate pandas code to transform data

    Args:
        state (State): Taipy GUI state
    """
    data_prompt = f"def transfom(transformed_data: pd.DataFrame) -> pd.DataFrame:\n  # {state.data_instruction}\n  return "
    output = query(
        {
            "inputs": data_prompt,
            "parameters": {
                "return_full_text": False,
            },
        }
    )[0]["generated_text"]
    output = output.split("\n")[0]
    state.transformed_data = pd.DataFrame(eval("state." + output))
    notify(state, "success", "Data Updated!")
    print(f"Data transformation code: {output}")


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

<|Original Data|expandable|expanded=True|
<|{data}|table|width=100%|page_size=5|filter=True|>
|>

## Enter your instruction to **modify**{: .color-primary} data here:
**Example:** Sum SALES grouped by COUNTRY
<|{data_instruction}|input|on_action=modify_data|class_name=fullwidth|change_delay=1000|>

<|Reset Transformed Data|button|on_action=reset_data|>

<|Transformed Data|expandable|expanded=True|
<|{transformed_data}|table|width=100%|page_size=5|rebuild|filter=True|>
|>

## Enter your instruction to **plot**{: .color-primary} data here:
**Example:** Plot a pie chart of SALES by COUNTRY titled Sales by Country
<|{plot_instruction}|input|on_action=plot|class_name=fullwidth|change_delay=1000|>

<|part|partial={p}|>
"""

gui = Gui(page)
p = gui.add_partial(
    """<|{transformed_data.groupby('COUNTRY').SALES.sum().reset_index()}|chart|type=pie|values=SALES|labels=COUNTRY|title=Sales by Country|>"""
)
gui.run(port=6969)
