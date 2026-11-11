# CampusFlow AI

An agentic campus service assistant for lab bookings, attendance checks, and leave applications. It uses a hosted, OpenAI-compatible inference API, FastAPI, LangGraph, and PostgreSQL. Campus service tools are simulated for the project; the model never connects to the database directly.

## What it demonstrates

- Turns a request into one or more service steps.
- Selects validated campus tools and observes their results.
- Retries transient failures, replans when possible, and escalates when action needs a person.
- Logs plans, tool calls, outcomes, and escalations without storing hidden model reasoning.
- Includes a deterministic rule-based baseline endpoint for later evaluation.

## Quick start

1. Install Python 3.11 or newer and Docker Desktop.
2. Copy `.env.example` to `.env` and add an API key for your OpenAI-compatible inference provider. Set `MODEL_BASE_URL` and `MODEL_NAME` to the provider's values.
3. Start PostgreSQL: `docker compose up -d db`
4. Create a virtual environment and install dependencies:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

5. Start the API: `uvicorn app.main:app --reload`
6. Open `http://127.0.0.1:8000/docs` to try the API.

The agent uses a small simulated campus dataset. For local development without a model key, set `AGENT_MODE=demo`; this runs a deterministic planner through the same graph and tools. Set `AGENT_MODE=llm` for hosted inference.

## Example request

`POST /api/requests`

```json
{
  "student_id": "S1001",
  "message": "Check my attendance and find an available lab for robotics tomorrow afternoon",
  "confirm_actions": false
}
```

For leave applications, the agent prepares a draft and asks for confirmation before submission. Confirmation is explicit: resend with `confirm_actions: true` after reviewing the proposed details.

## Main routes

- `GET /health` — service status
- `POST /api/requests` — execute an agent request
- `POST /api/baseline` — run the scripted rule-based baseline
- `GET /api/tasks/{task_id}` — retrieve task status and event log
- `GET /api/metrics` — summary metrics for agent and baseline runs

## GitHub

This folder is ready to initialize as a Git repository. Review `.env` before committing; secrets are excluded by `.gitignore`. To publish it, create an empty GitHub repository and then run the commands shown by GitHub for pushing an existing repository. No remote or account has been configured here.

## Project layout

```text
app/
  agent/       LangGraph workflow, hosted model adapter, and demo planner
  api/         request and metrics routes
  services/    validated simulated campus tools
  storage/     SQLAlchemy models and database session
  main.py
web/           lightweight chat interface
```
