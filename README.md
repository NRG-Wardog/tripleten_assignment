# AI Code Reviewer — Nebius Integration (Computer Use Demo)

This is a minimally changed fork of Anthropic’s **computer-use-demo** wired to use **Nebius AI** as the LLM backend.  
It keeps the Streamlit UI and the “computer use” tools (mouse/keyboard/screenshot), but swaps Anthropic calls for Nebius.

This README covers **only the required parts** of the assignment: run the baseline, adapt to Nebius, and provide a brief write-up on the adaptation and evaluation.

---

## Quick Start

### 0) Prereqs
- Docker installed
- A Nebius Studio account and **API key**
- The original repo cloned (this folder):  
  `anthropic-quickstarts/computer-use-demo`

### 1) Create a `.env` file **in the repo root** (same folder that contains `computer_use_demo/`)
```dotenv
# REQUIRED: switch provider
API_PROVIDER=nebius

# REQUIRED: Nebius auth
NEBIUS_API_KEY=YOUR_API_KEY_HERE
NEBIUS_FOLDER_ID=default

# REQUIRED for the virtual desktop size used by the “computer” tool
WIDTH=1280
HEIGHT=800

# OPTIONAL but recommended: set a valid model URI from your Nebius account
# Go to Nebius Studio → Models → copy the exact URI.
# Example (adjust to what you actually have access to):
# NEBIUS_MODEL_URI=gpt://default/ai-deepseek/DeepSeek-R1:free
# NEBIUS_MODEL_URI=gpt://default/ai-deepseek/DeepSeek-R1:latest
```

> If you see `invalid model_uri`, set `NEBIUS_MODEL_URI` to an actual model in your Nebius project.

### 2) Run (macOS/Linux bash)
```bash
docker run --rm -it   -v "${PWD}:/app"   -w /app/computer_use_demo   --env-file ../.env   -e PYTHONPATH=/app   -p 8501:8501   python:3.11   bash -lc "pip install -r requirements.txt && streamlit run streamlit.py"
```

### 2b) Run (Windows PowerShell)
From the **repo root** (where `.env` lives):
```powershell
docker run --rm -it `
  -v "${PWD}:/app" `
  -w /app/computer_use_demo `
  --env-file ../.env `
  -e PYTHONPATH=/app `
  -p 8501:8501 `
  python:3.11 `
  bash -lc "pip install -r requirements.txt && streamlit run streamlit.py"
```

### 3) Use it
Open **http://localhost:8501**.

In the left sidebar:
- **API Provider** → `Nebius`
- **Model** → you can leave as-is (cosmetic) or paste a model name; the real routing uses `NEBIUS_MODEL_URI`.
- Tool version: either `computer_use_20250124` or the default works.

Try in chat:
- `Say hello` → expect a normal text reply.
- `Open Firefox and go to example.com` → the agent should click around; screenshots will appear in the chat.

---

## What Changed (Minimal Diff)

- `computer_use_demo/loop.py`  
  - Added `APIProvider.NEBIUS` branch.  
  - When selected, we build a `NebiusClient` instead of an Anthropic client, then proceed with the same sampling loop.

- `computer_use_demo/streamlit.py`  
  - Added Nebius to the provider list and default model mapping.  
  - No Anthropic key required if `API_PROVIDER=nebius`.

- `computer_use_demo/nebius_client.py` **(new)**  
  - Small adapter that **mimics** the Anthropic SDK surface the demo expects:
    `client.beta.messages.with_raw_response.create(...)`.
  - Converts the demo’s `system` + `messages` into **Nebius Studio** chat format and calls:
    ```
    POST https://api.studio.nebius.com/v1/chat/completions
    ```
  - Builds `modelUri` from `NEBIUS_MODEL_URI` or a safe default, and returns a minimal response object compatible with the demo’s UI/logs.

- `computer_use_demo/requirements.txt`  
  - Ensures `httpx` is present (used by the adapter). Other pins match upstream demo.

Everything else (tools for mouse/keyboard/screenshot, desktop setup, Streamlit UI, logs) remains unchanged.

---

## Required Smoke Tests

1) **Plain text**  
   Input: `Say hello`  
   Expected: A simple greeting back.

2) **Open a program**  
   Input: `Open Firefox`  
   Expected: The agent clicks the Firefox icon; a screenshot appears.

3) **Navigate and extract**  
   Input: `In Firefox, go to example.com and tell me the H1`  
   Expected: The agent navigates and returns **“Example Domain.”**

If these pass, the required adaptation is working.

---

## Troubleshooting

- **`NEBIUS_API_KEY is not set in the environment.`**  
  Put it in `.env` at the repo root. Make sure your `--env-file ../.env` path matches where you run Docker.  
  (If you run with `-w /app/computer_use_demo`, the `.env` one level up is `../.env`.)

- **`invalid model_uri` (Nebius 400)**  
  Your account may not have that model or tag. In Nebius Studio → **Models**, copy the exact URI and put it in `.env`:
  ```
  NEBIUS_MODEL_URI=gpt://<folder>/<provider>/<model>:<tag>
  ```
  Example: `gpt://default/ai-deepseek/DeepSeek-R1:free`.

- **`WIDTH, HEIGHT must be set` (AssertionError)**  
  Add `WIDTH` and `HEIGHT` to `.env` (e.g., `1280x800`).

- **`ModuleNotFoundError: computer_use_demo.loop`**  
  Include `-e PYTHONPATH=/app` in `docker run`, and make sure you’re running with  
  `-w /app/computer_use_demo` and mounted the repo at `/app`.

- **Provider radio error (`Expected an EnumMeta/Type`)**  
  Usually a stale container/code mismatch. Re-run the full `docker run …` command above so it uses the current files.

- **400 Bad Request with little detail**  
  Almost always the model URI. Set a known-good `NEBIUS_MODEL_URI`.

---

## Adaptation Summary (Required Write-up)

**Goal:** Use Nebius Studio instead of Anthropic while preserving the agent/tool loop.

**Approach:**  
We built a thin **adapter** (`nebius_client.py`) that exposes the same call site the demo expects (`client.beta.messages.with_raw_response.create`). Inside the adapter, we:

- Map the demo’s `system` + conversation **text** blocks into Nebius **chat** format (`[{role, text}]`).
- Call the Nebius **chat completions** endpoint and parse the assistant’s reply.
- Return a small object that the Streamlit logger and the sampling loop can understand (so the rest of the demo remains untouched).

**Key differences handled:**
- **Different request/response schema:** Anthropic’s beta message blocks vs. Nebius chat. Solved with the adapter.
- **Model URI strictness:** Nebius requires a valid `gpt://…` URI. Exposed via `.env` as `NEBIUS_MODEL_URI`.
- **UTF-8 input:** Ensured headers/body are UTF-8 so non-ASCII (e.g., Hebrew) works.

---

## How I Would Evaluate This Agent (Required Write-up)

1) **Task Success Rate (TSR)**  
   Percentage of tasks completed without human help (e.g., “open Firefox → navigate → confirm H1”).  
   - Define success concretely (DOM text match, file created, URL reached).  
   - Track per-scenario over many runs.

2) **Tool Efficiency & Latency**  
   - **Median End-to-End Latency:** user message → final answer.  
   - **Tool Step Count:** average number of clicks/keystrokes per successful task. Lower is better.  
   These catch regressions when changing model, prompts, or desktop settings.

*(Nice to have: error taxonomy — “misclick”, “element not found”, “timeout”; and human preferences for textual outputs.)*

---

## Repo Layout

```
computer_use_demo/
  loop.py            # provider switch; Nebius branch added
  streamlit.py       # provider list + defaults include Nebius
  nebius_client.py   # adapter (new)
  requirements.txt   # httpx ensured; otherwise upstream pins
  tools/             # unchanged tool stack: computer, bash, edit, ...
.env                 # your local config (not committed)
README.md            # this file
```

---

## Optional: Local (non-Docker) Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r computer_use_demo/requirements.txt
export PYTHONPATH=$PWD
export $(cat .env | xargs)  
cd computer_use_demo
streamlit run streamlit.py
```
