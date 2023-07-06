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

LOG_PATH = "logs.txt"


def log(message: str) -> None:
    """
    Logs message to file

    Args:
        message (str): Message to log
    """
    with open(LOG_PATH, "a") as f:
        f.write(message + "\n")


CONTEXT_PATH = "context_data.csv"
DATA_PATH = "sales_data_sample.csv"

context_data = pd.read_csv(CONTEXT_PATH, sep=";")
data = pd.read_csv(DATA_PATH, sep=",", encoding="ISO-8859-1")

data["ORDERDATE"] = pd.to_datetime(data["ORDERDATE"])
data = data.sort_values(by="ORDERDATE")

data_columns = data.columns.tolist()
data_columns_str = " ".join(data.columns.tolist())
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
    print(f"Plot code: {output_code}")
    log(f"[PLOT] {output_code}")

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
    log(f"[PLOT] {state.plot_instruction}")
    state.result = plot_prompt(state.plot_instruction)
    state.p.update_content(state, state.result)
    notify(state, "success", "Plot Updated!")
    log(f"[PLOT] Plot Successful!")


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
    log(f"[DATA] {state.data_instruction}")
    current_prompt = f"def transform(transformed_data: pd.DataFrame) -> pd.DataFrame:\n  # {state.data_instruction}\n  # transformed_data has columns: {data_columns_str}\n  return "
    output = ""
    final_result = ""

    # Re-query until the output contains the closing tag
    timeout = 0
    while "\n" not in output and timeout < 10:
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
    final_result = final_result.split("\n")[0]

    if "groupby" in final_result and "reset_index" not in final_result:
        final_result = f"{final_result}.reset_index()"

    print(f"Data transformation code: {final_result}")
    log(f"[DATA] {final_result}")
    try:
        state.transformed_data = pd.DataFrame(eval("state." + final_result))
        notify(state, "success", f"Data Updated with code:{final_result}")
        log(f"[DATA] Data Manipulation Successful!")
    except Exception as ex:
        notify(state, "error", f"Error with code {final_result} --- {ex}")


def reset_data(state) -> None:
    """
    Resets transformed data to original data and resets plot

    Args:
        state (State): Taipy GUI state
    """
    log("[DATA] Reset Data")
    state.transformed_data = state.data.copy()
    state.p.update_content(state, "")


def report_feedback(state) -> None:
    """
    Saves user feedback to file

    Args:
        state (State): Taipy GUI state
    """
    log(f"[REPORT] {state.report}")
    notify(state, "success", "Feedback Submitted!")


transformed_data = data.copy()
data_instruction = ""
plot_instruction = ""
result = ""
report = ""


page = """
# TalkTo**Taipy**{: .color-primary} Alpha Testing

## **Modify**{: .color-primary} and **Plot**{: .color-primary} your data using natural language

<p align="center">
  <img src="media/animated.gif" alt="Example" width="80%"/>
</p>

## Report issues or send feedback here:

<|{report}|input|on_action=report_feedback|class_name=fullwidth|change_delay=1000|label=Enter your feedback here|>

- Long prompts might cause errors

- If an error stays on the page, try refreshing the page

<|Original Data|expandable|expanded=True|
<|{data}|table|width=100%|page_size=5|>
|>

## Enter your instruction to **modify**{: .color-primary} the dataset here:
**Example:** Sum SALES grouped by COUNTRY
<|{data_instruction}|input|on_action=modify_data|class_name=fullwidth|change_delay=1000|label=Enter your data manipulation instruction here|>

<|Reset Transformed Data|button|on_action=reset_data|>

<|Transformed Data|expandable|expanded=True|
<|{transformed_data}|table|width=100%|page_size=5|rebuild|>
|>

## Enter your instruction to **plot**{: .color-primary} data here:
**Example:** Plot a pie chart of SALES by COUNTRY titled Sales by Country
<|{plot_instruction}|input|on_action=plot|class_name=fullwidth|change_delay=1000|label=Enter your plot instruction here|>

<|part|partial={p}|>
"""

log("[SYSTEM] Session Start")
gui = Gui(page)
p = gui.add_partial("")
gui.run(title="Talk To Taipy (alpha)")
