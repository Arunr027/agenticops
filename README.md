# AgenticOps — Stateful Multi-Agent Workflow Engine

AgenticOps is a Python-based workflow engine that uses AI planning, tool execution, verification, and persistent checkpoints to run tasks through a controlled multi-step workflow.

The project explores how to build more reliable agentic applications using LangGraph, Gemini, FastAPI, Pydantic, and Redis.

## Key Features

- **LLM-based planning:** Uses Gemini to generate structured workflow plans.
- **Tool execution:** Executes registered tools with validated arguments.
- **Workflow verification:** Checks execution results and determines workflow status.
- **Retry handling:** Supports retries for eligible execution failures.
- **Execution limits:** Restricts the number of workflow steps and limits tool execution time.
- **Checkpoint persistence:** Uses Redis-backed LangGraph checkpoints to preserve workflow state.
- **Session retrieval:** Provides API endpoints to retrieve workflow results and history.
- **Execution timing:** Records tool execution duration in milliseconds.
- **Structured error handling:** Reports planning and execution failures.
- **Automated testing:** Includes tests for planning, execution, retries, timeouts, persistence, and API behavior.

## Architecture

```text
Client
  |
  v
FastAPI
  |
  v
Planner
  |
  v
Executor --------> Registered Tools
  |                       |
  v                       v
Verifier <---------- Tool Results
  |
  v
Workflow Result

Redis <--------> LangGraph Checkpoints
```

### Main Components

| Component | Responsibility |
|---|---|
| FastAPI | Exposes workflow endpoints |
| Planner | Generates and validates workflow plans |
| Executor | Runs registered tools and handles eligible retries |
| Verifier | Checks results and determines completion or failure |
| Registered tools | Perform supported operations |
| Redis | Stores workflow checkpoints |
| Pydantic | Validates plans, arguments, and structured data |
| Pytest | Tests workflow behavior and reliability |

## Technology Stack

- Python
- FastAPI
- LangGraph
- LangGraph Redis Checkpointer
- Google Gemini API
- Pydantic
- Redis
- Pytest

## Project Structure

```text
Agentic-ops/
├── app/
│   ├── main.py
│   ├── workflow.py
│   ├── llm_planner.py
│   ├── tools.py
│   ├── models.py
│   ├── config.py
│   └── session_service.py
├── tests/
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

This shows the main project modules. Additional files may exist inside the `app/` and `tests/` directories.

## Prerequisites

- Python installed
- Redis running locally or through Docker
- A Gemini API key from Google AI Studio
- Git, if you want to clone or publish the repository

## Setup

### 1. Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd Agentic-ops
```

Replace the placeholder with your actual GitHub repository URL.

### 2. Create a virtual environment

**Windows Command Prompt:**

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

**Windows PowerShell:**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Configure environment variables

Copy `.env.example` to `.env` and configure the required values.

Example configuration:

```dotenv
APP_NAME=AgenticOps
APP_ENV=development
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=your_available_gemini_model
REDIS_URL=redis://localhost:6380/0
TOOL_TIMEOUT_SECONDS=10
```

Use the environment variable names and defaults supported by `app/config.py`. The Gemini model must be available to your Google AI project, and the Redis URL must match your running Redis instance.

**Security:** Never commit `.env` or publish your Gemini API key.

### 5. Start Redis

Make sure Redis is running and reachable at the URL configured in `.env`.

For the local development setup, Redis is configured on port `6380`. If your Redis instance uses another port, update `REDIS_URL` accordingly.

### 6. Start the API

From the project root, run:

```bash
python -m uvicorn app.main:app --reload --port 8001
```

The API will be available at:

- Health check: http://127.0.0.1:8001/health
- Interactive API documentation: http://127.0.0.1:8001/docs

## API Endpoints

### 1. Health Check

**Method:** `GET`

**Endpoint:** `/health`

Checks whether the application is running.

### 2. Create a Workflow

**Method:** `POST`

**Endpoint:** `/workflows`

Example request:

```json
{
  "task": "Add 15 and 27",
  "max_steps": 5
}
```

A successful response for this supported task may look like:

```json
{
  "session_id": "generated-session-id",
  "status": "completed",
  "answer": "42",
  "steps_executed": 1,
  "errors": []
}
```

The session ID is illustrative. The API generates a session ID if one is not supplied. The actual response fields depend on the response model and execution result.

### 3. Retrieve a Workflow

**Method:** `GET`

**Endpoint:** `/workflows/{session_id}`

Retrieves the saved workflow state for a session, including its result and status.

Replace `{session_id}` with the actual session ID returned when creating a workflow.

### 4. Retrieve Workflow History

**Method:** `GET`

**Endpoint:** `/workflows/{session_id}/history`

Retrieves the available checkpoint history and related session information.

### 5. Test the API using Swagger

1. Start the FastAPI server.
2. Open http://127.0.0.1:8001/docs.
3. Expand `POST /workflows`.
4. Select **Try it out**.
5. Enter a supported task, such as adding two numbers.
6. Select **Execute**.
7. Review the response and copy the returned session ID.
8. Use the session ID with the workflow retrieval and history endpoints.

## Example Workflow

A simple supported task is adding two numbers.

Request:

```json
{
  "task": "Add 15 and 27",
  "max_steps": 5
}
```

Expected result for the tested deterministic fallback:

```text
Answer: 42
Status: completed
Steps executed: 1
Errors: []
```

The API also returns a session ID that can be used to retrieve the workflow result.

More complex tasks may require Gemini planning and can fail when the API quota is exhausted or the requested operations are unsupported by the registered tools.

## Run Tests

Run the complete test suite from the project root:

```bash
python -m pytest -q
```

Latest recorded test result during development:

```text
45 passed, 14 warnings
```

The warnings were dependency deprecation warnings from `langsmith` and `google.genai`, rather than test failures. Test results may vary after code or dependency changes.

## Reliability and Error Handling

AgenticOps includes:

- Structured plan validation before tool execution.
- Registered-tool checks and argument validation.
- Workflow step limits.
- Tool execution timeout handling.
- Retries for eligible failures.
- Redis-backed workflow checkpoints.
- Tool execution duration tracking.
- Clear error reporting for Gemini quota exhaustion.
- Session retrieval after workflow execution.

Gemini free-tier quotas can prevent live planning requests. When this happens, a workflow may fail if the task cannot be planned using the available fallback. Simple supported tasks may still complete through the deterministic fallback.

## Current Limitations

- The available tools are limited to predefined operations.
- Tasks requiring external research, arbitrary file access, or unrestricted actions are not supported by the current tool registry.
- Successful live Gemini planning still needs end-to-end verification when API quota is available.
- The project focuses on the workflow engine and API rather than a dedicated frontend.
- Redis must be available for checkpoint persistence.
- The sample configuration must be adjusted for the target environment.

## Future Improvements

- Add a shared cooldown for Gemini quota exhaustion.
- Add workflow-wide execution duration metrics.
- Improve API-facing execution event streaming.
- Add Docker-based deployment instructions and a reproducible environment.
- Add a demo recording showing planning, execution, verification, and checkpoint recovery.
- Add more registered tools and broader workflow integration tests.

## Project Status

The core workflow engine and automated test suite are working in the local development environment. The latest recorded test run completed with **45 passing tests**.

Live Gemini planning remains subject to API quota availability and still requires a successful end-to-end verification.

## License

No license has been selected yet. Choose and add a license before publishing the project publicly.
