# 🚀 AI CRM for HCP Interactions

An AI-powered CRM system for managing Healthcare Professional (HCP) interactions using FastAPI, LangGraph, LangChain, and Groq LLMs.

The system enables users to manage HCP records, log interactions, track follow-ups, and interact with CRM data through natural language conversations powered by an AI agent.

---

# 🎯 Problem Statement

Field representatives frequently interact with healthcare professionals and need a structured way to:

* Maintain HCP records
* Log discussions and meetings
* Schedule and track follow-ups
* Retrieve interaction history
* Update CRM records efficiently

This project combines traditional CRM functionality with AI-powered workflows, allowing users to perform CRM operations using natural language instead of manually navigating multiple screens.

---

# ⚙️ Features Implemented

## 1. HCP Management

* Dynamic HCP creation during interaction logging
* Search-first workflow to avoid duplicate records
* Automatic enrichment of missing HCP details
* Search by:

  * HCP ID
  * Name
  * Hospital

---

## 2. Interaction Logging

Supports structured interaction recording:

* Doctor Name
* Hospital
* Specialization
* City
* Topic
* Notes
* Follow-up Action
* Follow-up Date

Features:

* Dynamic HCP creation if not found
* Reuses existing HCP records
* Updates missing HCP metadata when available

---

## 3. Follow-up Tracking

Supported statuses:

* pending
* completed
* cancelled
* no_follow_up

Capabilities:

* Multi-step planning
* Tool orchestration
* Tool chaining using intermediate outputs
* Structured JSON plan generation
* Dynamic tool execution
* Retry-based recovery with replanning
* Tool parameter validation
* Tool response validation
* Agent execution logging for debugging and traceability

# 📋 Agent Observability

The agent includes logging capabilities to improve debugging and traceability.

Logged events include:

* User requests
* Generated execution plans
* Retry attempts
* Tool execution failures
* Replanned workflows
* Final execution outcomes

This enables easier troubleshooting of LLM-generated workflows and supports iterative improvement of the agent.

---

## 4. Interaction Updates

Supports selective updates:

* Topic
* Follow-up Action
* Follow-up Date
* Follow-up Status
* Notes

Features:

* Partial updates
* Tracks updated fields
* Returns structured responses

---

## 5. Authentication & Security

Implemented JWT-based authentication:

* User Signup
* User Login
* Password Hashing
* JWT Access Tokens
* Protected Chat Endpoint

Only authenticated users can access AI-powered CRM workflows.

---

# 🤖 AI Agent Architecture

The system uses a LangGraph-based planning and execution agent.

Capabilities:

* Multi-step planning
* Tool orchestration
* Tool chaining
* Structured JSON plans
* Dynamic execution
* Retry-based recovery
* Validation of tool responses

---

## Example Workflow

User Query:

Show interaction history for Dr Himani from Apollo Hospital

Generated Plan:

1. Search HCP
2. Retrieve HCP Interaction History
3. Return CRM results

---

# 🛠️ LangGraph Tools

### SearchHCPTool

Search HCP records using:

* HCP ID
* Name
* Hospital

### LogInteractionTool

Creates CRM interaction records.

### EditInteractionTool

Updates interaction details.

### GetPendingFollowupsTool

Retrieves pending follow-up activities.

### GetHCPInteractionHistoryTool

Retrieves interaction history for a healthcare professional.

---

# 🔄 Retry & Validation Layer

The agent includes:

* Tool parameter validation
* Tool response validation
* Retry-based recovery mechanism
* Failure-aware replanning

This improves reliability when LLM-generated plans contain invalid inputs or execution failures.

---

# 🧪 Regression Testing

A regression testing suite is maintained using predefined CRM prompts.

Tests cover:

* HCP Search
* Interaction Logging
* Interaction History Retrieval
* Pending Follow-up Retrieval
* Interaction Updates
* Multi-step Tool Chaining
* Retry and Recovery Scenarios
* Authentication Validation

This helps detect regressions after code changes.

---

# 🏗️ Architecture

User
↓
Chat API
↓
LangGraph Planner
↓
Tool Execution Layer
↓
FastAPI APIs
↓
Database

---

# 🧠 Key Highlights

* AI-first CRM architecture
* Multi-step reasoning with LangGraph
* Dynamic tool orchestration
* Retry-aware execution framework
* Regression testing for agent workflows
* Execution logging and observability
* JWT-based authentication
* Structured CRM workflows
* Natural language interaction layer
* Production-style backend architecture

---

# 📌 Tech Stack

Backend

* FastAPI
* SQLAlchemy
* SQLite

AI

* LangGraph
* LangChain
* Groq
* Llama 3.3 70B Versatile

Authentication

* JWT
* Passlib
* Bcrypt

Database

* SQLite
* Easily extendable to PostgreSQL

---

# 🚀 How to Run

## 1. Clone Repository

git clone <repository-url>

cd ai-crm-hcp

---

## 2. Create Virtual Environment

python -m venv venv

venv\Scripts\activate

---

## 3. Install Dependencies

pip install -r requirements.txt

---

## 4. Configure Environment Variables

Create a .env file:

GROQ_API_KEY=your_api_key

SECRET_KEY=your_secret_key

---

## 5. Start Backend

uvicorn app.main:app --reload

---

## 6. Access API Documentation

http://127.0.0.1:8000/docs

---

# 🚧 Current Limitations

* Relative date expressions require more robust normalization
* Clarification flow for ambiguous user requests is not implemented yet
* Agent is currently stateless
* Certain complex CRM queries may require additional specialized tools
* Frontend interface is under development

---

# 🔮 Future Enhancements

* Conversational memory
* Clarification-based workflows
* React frontend
* PostgreSQL migration
* Role-based access control
* Response synthesis layer for user-friendly outputs
* Production deployment
* Advanced analytics and reporting
