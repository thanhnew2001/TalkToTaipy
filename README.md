# TaipyCopilot

<p align="center">
  <img src="media/app_pie.png" alt="App" width="100%"/>
</p>

Converts English sentences to Taipy Web App elements

## Current Scope:

TaipyCopilot works with few-shot learning on StarCoder.

Currently supports:
- line plots with multiple lines, colors and line styles
- bar charts with multiple bars, colors and orientation
- scatter plots with multiple data columns, colors
- title
- simple histograms
- simple pie charts

Known issues:
- When a prompt results in incorrect code, the app will show an error message and get stuck. To fix this, simply re-prompt and refresh the page.
- A too long prompt will cause StarCoder to repeat unfinished code which will cause a syntax error

## Setup

**Requires a Hugging Face API key in `app.py`** 

[How to get your Hugging Face API key](https://huggingface.co/docs/hub/security-tokens#:~:text=To%20create%20an%20access%20token,you're%20ready%20to%20go!)

**1.** Clone the repo

```bash	
git clone https://github.com/AlexandreSajus/TaipyLLM.git
```

**2.** Install requirements

```bash
pip install -r requirements.txt
```

**3.** Create a `secret.txt` text file next to `app.py` with your Hugging Face API key in it

**4.** Run `app.py`

```bash
python app.py
```