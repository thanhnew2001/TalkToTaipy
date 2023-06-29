from taipy.gui import Gui, notify

import re
import random
import pandas as pd
import requests

SECRET_PATH = "secret.txt"
with open(SECRET_PATH, "r") as f:
    API_TOKEN = f.read()

API_URL = "https://api-inference.huggingface.co/models/bigcode/starcoder"
headers = {"Authorization": f"Bearer {API_TOKEN}"}

CONTEXT_PATH = "context_data.csv"
DATA_PATH = "sales_data_sample.csv"
PROMPT_PATH = "data_prompt.txt"

# Read prompt from file
with open(PROMPT_PATH, "r") as f:
    PROMPT = f.read()

context_data = pd.read_csv(CONTEXT_PATH, sep=";")
data = pd.read_csv(DATA_PATH, sep=",", encoding="ISO-8859-1")

data["ORDERDATE"] = pd.to_datetime(data["ORDERDATE"])
data = data.sort_values(by="ORDERDATE")

data_columns = data.columns.tolist()
context_columns = ["Sales", "Revenue", "Date", "Usage", "Energy"]

# Replace column names in the context with column names from the data
context = ""
for instruction, code in zip(context_data["instruction"], context_data["code"]):
    example = f"{instruction}\n{code}\n"
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

    # Check if the output code is valid
    pattern = r"<.*\|chart\|.*>"
    if bool(re.search(pattern, output_code)):
        return output_code
    else:
        raise Exception("Generated code is incorrect")


def plot(state) -> None:
    """
    Prompt StarCoder to generate Taipy GUI code when user inputs plot instruction

    Args:
        state (State): Taipy GUI state
    """
    state.result = plot_prompt(state.plot_instruction)
    state.p.update_content(state, state.result)
    notify(state, "success", "Plot Updated!")
    print(f"Plot code: {state.result}")


def on_exception(state, function_name: str, ex: Exception) -> None:
    """
    Catches exceptions and notifies user in Taipy GUI

    Args:
        state (State): Taipy GUI state
        function_name (str): Name of function where exception occured
        ex (Exception): Exception
    """
    notify(state, "error", f"An error occured in {function_name}: {ex}")


def modify_data(state) -> None:
    """
    Prompts StarCoder to generate pandas code to transform data

    Args:
        state (State): Taipy GUI state
    """
    # Replace in PROMPT _ with the data instruction
    data_prompt = PROMPT.replace("@", state.data_instruction)
    output = ""
    final_result = data_prompt

    timeout = 0
    while "return transformed_data" not in final_result and timeout < 10:
        output = query(
            {
                "inputs": data_prompt + output,
                "parameters": {
                    "return_full_text": False,
                },
            }
        )[0]["generated_text"]
        timeout += 1
        final_result += output

    # In final_result, parse line by line and remove lines after the return statement
    final_result = final_result.split("\n")
    for i, line in enumerate(final_result):
        if "return" in line:
            final_result = final_result[: i + 1]
            break
    # Rejoin the lines
    final_result = "\n".join(final_result)
    # Execute the code
    exec(
        final_result
        + "\nstate.transformed_data = pd.DataFrame(transform(state.transformed_data))"
    )
    notify(state, "success", "Data Updated!")
    print(f"Data transformation code: {final_result}")


def reset_data(state) -> None:
    """
    Resets transformed data to original data and resets plot

    Args:
        state (State): Taipy GUI state
    """
    state.transformed_data = state.data.copy()
    state.p.update_content(state, "")


transformed_data = data.copy()
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
p = gui.add_partial("")
gui.run()
