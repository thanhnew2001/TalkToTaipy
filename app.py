from taipy.gui import Gui, notify

from pandasai import PandasAI
from pandasai.llm.starcoder import Starcoder

import pandas as pd

SECRET_PATH = "secret.txt"
with open(SECRET_PATH, "r") as f:
    API_TOKEN = f.read()

llm = Starcoder(api_token=API_TOKEN)
pandas_ai = PandasAI(llm=llm, verbose=True)

DATA_PATH = "sales_data_sample.csv"

original_data = pd.read_csv(DATA_PATH, sep=",", encoding="ISO-8859-1")
original_data["ORDERDATE"] = pd.to_datetime(original_data["ORDERDATE"])
original_data = original_data.sort_values(by="ORDERDATE")

user_input = ""
data = original_data.copy()


def modify_data(state) -> None:
    """
    Prompts StarCoder using PandasAI to modify or plot data
    """
    pandasai_output = pandas_ai(state.data, state.user_input)
    # Parse if output is DataFrame, Series, string...
    if isinstance(pandasai_output, pd.DataFrame):
        state.data = pandasai_output
    elif isinstance(pandasai_output, pd.Series):
        state.data = pd.DataFrame(pandasai_output).reset_index()
    else:
        state.data = pd.DataFrame([pandasai_output])


def reset_data(state) -> None:
    """
    Resets data to original data
    """
    state.data = original_data.copy()
    state.p = ""


page = """
# TalkTo**Taipy**{: .color-primary}

<|{user_input}|input|on_action=modify_data|class_name=fullwidth|change_delay=1000|label=Enter your instruction here|>

<|{data}|table|width=100%|page_size=5|rebuild|>

<|part|partial={p}|>

<|Reset to Original Data|button|on_action=reset_data|>
"""

gui = Gui(page)
p = gui.add_partial("")
gui.run(title="Talk To Taipy (alpha)")
