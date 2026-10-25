# \# Support Copilot AI

# 

# An AI-powered customer support and operations assistant for quick-commerce platforms, built around four progressively capable AI approaches: \*\*LLM, RAG, AI Agents, and Agentic AI\*\*.

# 

# Support Copilot helps answer customer queries, retrieve policy information, inspect operational data, and propose actions for human review through a unified interface.

# 

# \## Overview

# 

# The project evolves a basic AI experimentation notebook into a full-stack application with a streaming interface, hybrid document retrieval, guarded SQL execution, multi-agent orchestration, and human-in-the-loop approvals.

# 

# \### Key Features

# 

# \- \*\*Four AI modes:\*\* Compare LLM, Retrieval-Augmented Generation (RAG), tool-calling agents, and multi-agent orchestration.

# \- \*\*Hybrid RAG:\*\* Combines BM25 keyword retrieval with vector embeddings and Reciprocal Rank Fusion (RRF).

# \- \*\*Policy-grounded answers:\*\* Retrieves relevant passages from policy PDFs with page-level references.

# \- \*\*Tool-calling agents:\*\* Access order summaries, search policies, execute guarded SQL queries, and propose operational actions.

# \- \*\*Agentic orchestration:\*\* Coordinates specialist agents and synthesizes their results.

# \- \*\*Human-in-the-loop approvals:\*\* Routes proposed actions for human review instead of executing them automatically.

# \- \*\*Live execution traces:\*\* Streams agent plans, tool calls, retrieved passages, and execution details to the frontend.

# \- \*\*Operations dashboard:\*\* Presents operational analytics and information queried by the agents.

# \- \*\*Run history and feedback:\*\* Stores execution traces and supports thumbs-up/thumbs-down feedback.

# \- \*\*Evaluation and testing:\*\* Includes automated tests and an evaluation suite for tool usage, factual coverage, and refusals.

# 

# \## Architecture

# 

# ```text

# React + Vite Frontend

# &#x20;       |

# &#x20;       | Server-Sent Events (SSE)

# &#x20;       v

# FastAPI Backend

# &#x20;       |

# &#x20;       +-- LLM

# &#x20;       |     Gemini generation and embeddings

# &#x20;       |

# &#x20;       +-- RAG Pipeline

# &#x20;       |     PDF → Chunks → BM25 + Vectors → RRF

# &#x20;       |

# &#x20;       +-- Agent Tools

# &#x20;       |     Order Summary · Policy Search

# &#x20;       |     Guarded SQL · Web Search (optional)

# &#x20;       |     Proposed Actions

# &#x20;       |

# &#x20;       +-- Agentic Supervisor

# &#x20;       |     Planning → Specialist Agents → Synthesis

# &#x20;       |

# &#x20;       +-- Data and Operations

# &#x20;             Read-only SQLite queries

# &#x20;             Run history · Traces · Approvals · Feedback

# ```

# 

# \## AI Modes

# 

# | Mode | Approach | Purpose |

# |---|---|---|

# | LLM | Direct model generation | Answer queries using the language model |

# | RAG | Retrieval-augmented generation | Ground responses in relevant policy documents |

# | AI Agent | Model-driven tool calling | Retrieve order information, search policies, and query operational data |

# | Agentic AI | Supervisor and specialist agents | Coordinate multi-step tasks and combine specialist results |

# 

# \## Technology Stack

# 

# | Layer | Technologies |

# |---|---|

# | Frontend | React, Vite, JavaScript, CSS |

# | Backend | Python, FastAPI |

# | Language model | Google Gemini API |

# | Retrieval | BM25, vector embeddings, Reciprocal Rank Fusion |

# | Data storage | SQLite |

# | Streaming | Server-Sent Events (SSE) |

# | Testing | Pytest, custom evaluation scripts |

# | Deployment | Docker, Docker Compose, Render, Vercel |

# | CI | GitHub Actions |

# 

# \## Getting Started

# 

# \### Prerequisites

# 

# \- Python installed

# \- Node.js and npm installed

# \- A Google Gemini API key for model-powered responses

# \- Git and Docker, if required for containerized execution

# 

# \### 1. Clone the Repository

# 

# ```bash

# git clone https://github.com/Tanvi-1496/support-copilot-ai-agent-rag.git

# cd support-copilot-ai-agent-rag/blinkit-copilot

# ```

# 

# \### 2. Configure the Backend

# 

# ```bash

# cd backend

# python -m venv .venv

# ```

# 

# Activate the virtual environment.

# 

# \*\*Windows PowerShell:\*\*

# 

# ```powershell

# .venv\\Scripts\\Activate.ps1

# ```

# 

# \*\*Git Bash:\*\*

# 

# ```bash

# source .venv/Scripts/activate

# ```

# 

# Install dependencies:

# 

# ```bash

# pip install -r requirements.txt

# ```

# 

# Create your local environment file:

# 

# ```bash

# cp .env.example .env

# ```

# 

# On Windows, you can also copy `.env.example` to `.env` using File Explorer.

# 

# Add your API key to `backend/.env`:

# 

# ```env

# GOOGLE\_API\_KEY=your\_actual\_api\_key

# ```

# 

# Keep real credentials in `.env` only. Never commit API keys or other secrets to GitHub.

# 

# Start the backend:

# 

# ```bash

# python -m uvicorn app.main:app --reload --port 8000

# ```

# 

# \### 3. Start the Frontend

# 

# Open a second terminal:

# 

# ```bash

# cd frontend

# npm install

# npm run dev

# ```

# 

# Open the local URL printed by Vite, usually `http://localhost:5173`.

# 

# \## Testing and Evaluation

# 

# Run the automated backend tests:

# 

# ```bash

# cd backend

# python -m pytest -q

# ```

# 

# Run the model-based evaluation suite:

# 

# ```bash

# python -m evals.run\_evals

# ```

# 

# The evaluation suite requires a configured Gemini API key. Automated tests are designed to cover API behaviour, retrieval, agent execution, tool handling, and SQL safeguards.

# 

# \## Security and Guardrails

# 

# Security is built into the application's data-access and action workflows.

# 

# \- \*\*Read-only SQL:\*\* Restricts database queries through SQLite read-only access, authorization checks, statement limits, and result caps.

# \- \*\*Action approval:\*\* Proposed wallet credits, escalations, and store warnings are queued for human review rather than executed automatically.

# \- \*\*Tool isolation:\*\* Handles tool failures and unknown tools within the agent execution loop.

# \- \*\*Prompt-injection awareness:\*\* Tool outputs are treated as untrusted data in agent instructions.

# \- \*\*Credential hygiene:\*\* Environment files containing secrets are excluded from version control.

# 

# This is a demonstration project, not a production-ready financial or customer-support system.

# 

# \## Deployment

# 

# \### Docker Compose

# 

# From the project directory:

# 

# ```bash

# docker compose up --build

# ```

# 

# Open `http://localhost:8080` when the containers are running.

# 

# \### Backend

# 

# The backend includes deployment configuration for Render. Configure the required environment variables in the hosting dashboard, including:

# 

# \- `GOOGLE\_API\_KEY`

# \- `TAVILY\_API\_KEY`, if web search is enabled

# \- `CORS\_ORIGINS`, configured for the deployed frontend

# 

# Use the health endpoint `/api/health` to verify backend availability.

# 

# \### Frontend

# 

# The frontend can be deployed to Vercel. Set the project root to `frontend` and configure `VITE\_API\_URL` with the deployed backend URL.

# 

# Follow the repository's deployment configuration and hosting provider requirements when deploying.

# 

# \## Project Structure

# 

# ```text

# blinkit-copilot/

# ├── .github/

# │   └── workflows/

# │       └── ci.yml

# ├── backend/

# │   ├── app/

# │   │   ├── main.py

# │   │   ├── agents.py

# │   │   ├── tools.py

# │   │   ├── rag.py

# │   │   ├── llm.py

# │   │   ├── db.py

# │   │   ├── ops.py

# │   │   ├── queries.py

# │   │   └── analytics.py

# │   ├── data/

# │   ├── evals/

# │   ├── scripts/

# │   ├── tests/

# │   ├── requirements.txt

# │   └── Dockerfile

# ├── frontend/

# │   ├── src/

# │   │   ├── components/

# │   │   └── pages/

# │   ├── package.json

# │   └── Dockerfile

# ├── docker-compose.yml

# ├── render.yaml

# └── README.md

# ```

# 

# \## Current Limitations

# 

# \- Production authentication and role-based access control need to be implemented.

# \- Approved actions require integration with real payment or ticketing systems before execution.

# \- Persistent production storage and appropriate data-retention controls are needed for deployment.

# \- Retrieval quality, evaluation coverage, and observability can be expanded further.

# 

# The bundled demonstration data is synthetic and intended for development and evaluation.

# 

# \## Author

# 

# \*\*Tanvi Jaware\*\*

# 

# GitHub: \[@Tanvi-1496](https://github.com/Tanvi-1496)

# 

# \---

# 

# \*Support Copilot AI: combining retrieval, tool use, and agent orchestration for support and operations workflows.\*

