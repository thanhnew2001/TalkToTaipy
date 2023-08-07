from taipy.gui import Gui, notify

from pandasai import PandasAI
from pandasai.llm.starcoder import Starcoder
from pandasai.middlewares.base import Middleware

import pandas as pd
import matplotlib.pyplot as plt

SECRET_PATH = "secret.txt"
with open(SECRET_PATH, "r") as f:
    API_TOKEN = f.read()


class PlotMiddleware(Middleware):
    def run(self, code: str) -> str:
        code = f"from matplotlib import pyplot as plt\n{code}"
        # Remove lines with plt.show
        code = "\n".join([line for line in code.split("\n") if "plt.show" not in line])
        # Remove lines with plt.close
        code = "\n".join([line for line in code.split("\n") if "plt.close" not in line])
        print(code)
        return code


llm = Starcoder(api_token=API_TOKEN)
pandas_ai = PandasAI(llm=llm, verbose=True, enable_cache=False)
pandas_ai.add_middlewares(PlotMiddleware())

DATA_PATH = "sales_data_sample.csv"

original_data = pd.read_csv(DATA_PATH, sep=",", encoding="ISO-8859-1")
original_data["ORDERDATE"] = pd.to_datetime(original_data["ORDERDATE"])
original_data = original_data.sort_values(by="ORDERDATE")

user_input = ""
data = original_data.copy()
content = None
i = 0


def modify_data(state) -> None:
    """
    Prompts StarCoder using PandasAI to modify or plot data
    """
    global i
    notify(state, "info", "Running query...")
    state.data = original_data.copy()
    state.content = None
    pandasai_output = pandas_ai(state.data, state.user_input)
    # Parse if output is DataFrame, Series, string...
    if isinstance(pandasai_output, pd.DataFrame):
        state.data = pandasai_output
        notify(state, "success", "Data successfully modified!")
    elif isinstance(pandasai_output, pd.Series):
        state.data = pd.DataFrame(pandasai_output).reset_index()
        notify(state, "success", "Data successfully modified!")
    # If int, str, float, bool
    elif isinstance(pandasai_output, (int, str, float, bool)):
        state.data = pd.DataFrame([pandasai_output])
        notify(state, "success", "Data successfully modified!")
    # Else is matplotlib plot
    else:
        i += 1
        plt.tight_layout()
        plt.savefig(f"plot{i}.png", dpi=500)
        state.content = f"plot{i}.png"
        plt.close("all")
        notify(state, "success", "Plot successfully generated!")


def on_exception(state, function_name: str, ex: Exception) -> None:
    """
    Catches exceptions and notifies user in Taipy GUI

    Args:
        state (State): Taipy GUI state
        function_name (str): Name of function where exception occured
        ex (Exception): Exception
    """
    notify(state, "error", f"An error occured in {function_name}: {ex}")


def reset_data(state) -> None:
    """
    Resets data to original data, resets plot
    """
    state.data = original_data.copy()


def example1(state) -> None:
    """
    Runs an example prompt
    """
    state.user_input = "What are the 5 most profitable cities?"
    modify_data(state)


def example2(state) -> None:
    """
    Runs an example prompt
    """
    state.user_input = "Plot in a bar chart sales of the 5 most profitable cities, sorted descending, with ylabel 'Sales ($)'"
    modify_data(state)


def example3(state) -> None:
    """
    Runs an example prompt
    """
    state.user_input = "Plot sales by product line in a pie chart"
    modify_data(state)


page = """
# TalkTo**Taipy**{: .color-primary}

<|Example Instructions|expandable|expanded=True|
<|What are the 5 most profitable cities?|button|on_action=example1|>

<|Plot sales by product line in a pie chart|button|on_action=example3|>

<|Plot in a bar chart sales of the 5 most profitable cities, sorted descending, with ylabel 'Sales ($)'|button|on_action=example2|>
|>

<|{user_input}|input|on_action=modify_data|class_name=fullwidth|label=Enter your instruction here|>

<center>
<|{content}|image|width=50%|>
</center>

<|Dataset|expandable|expanded=True|
<|{data}|table|width=100%|page_size=5|rebuild|>
|>

<|Reset Data|button|on_action=reset_data|>
"""

gui = Gui(page)
gui.run(title="Talk To Taipy")
