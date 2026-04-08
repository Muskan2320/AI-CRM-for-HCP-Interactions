# 🚀 AI CRM for HCP Interactions

This project is an AI-first CRM system designed for managing interactions with Healthcare Professionals (HCPs). It enables structured logging, intelligent updates, and AI-powered workflows using LangGraph and LLMs.

---

## 🎯 Problem Statement

The goal is to build a CRM system that allows field representatives to efficiently log, track, and manage interactions with healthcare professionals. The system supports both structured data entry and AI-assisted workflows to improve productivity, data consistency, and follow-up tracking.

---

## ⚙️ Features Implemented

### 1. HCP Management
- Dynamic creation of HCP records during interaction logging  
- Search-first approach to avoid duplicate entries  
- Auto-update of missing HCP fields (e.g., specialization, city)  

---

### 2. Interaction Logging
- Log interactions with structured data:
  - Doctor name, hospital  
  - Topic, notes  
  - Follow-up details  
- Smart handling of optional fields (stored only if provided)  

---

### 3. Follow-up Status Standardization
- Controlled values:
  - `pending`, `completed`, `cancelled`, `no_follow_up`  
- Ensures clean filtering and tracking  

---

### 4. Interaction Update (Edit Feature)
- Update interaction fields selectively  
- Returns structured response including updated fields  
- Supports partial updates (only changed fields are modified)  

---

### 5. HCP Search API
- Search by:
  - HCP ID (highest priority)  
  - Name  
  - Hospital  
- Default behavior: returns latest 10 HCPs  
- Flexible filtering for real-world usage  

---

### 6. Interaction & Follow-up Retrieval
- Fetch interaction history by HCP ID  
- Fetch pending follow-ups:
  - Supports optional date filtering  
  - Sorted by nearest follow-up date  

---

### 7. AI Integration (Groq + LangChain)
- Integrated Groq LLM (`llama-3.3-70b-versatile`)  
- End-to-end LLM pipeline working  
- Structured prompt design for reliable outputs  

---

### 8. LangGraph Tools Layer
- `SearchHCPTool` → fetch doctor details  
- `LogInteractionTool` → log interaction into CRM  
- `EditInteractionTool` → update existing interaction  
- `GetPendingFollowupsTool` → fetch follow-ups  
- `GetHCPInteractionHistoryTool` → fetch history  

---

### 9. LangGraph AI Agent (Core 🚀)
- Built a **plan-based AI agent using LangGraph**
- Capabilities:
  - Multi-step reasoning (tool chaining)  
  - Structured JSON planning  
  - Dynamic tool execution  
  - Ask-user fallback for missing inputs  

#### Example Workflow:
User Query:
Show interaction history of Dr Sharma

Agent Plan:
1. search_hcp → get hcp_id  
2. get_hcp_interaction_history → fetch data  

---

### 10. Intelligent Input Handling
- Extracts structured data from natural language  
- Asks for missing required inputs only when needed  
- Minimizes user friction  

---

## 🧪 How to Run Locally

### 1. Clone Repository
git clone <your-repo-url>
cd ai-crm-hcp

### 2. Setup Backend
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

### 3. Run FastAPI Server
uvicorn app.main:app --reload

### 4. Run AI Agent (Separate Terminal)
python app/langgraph/agent.py

---

## 🚧 Current Limitations
- Occasional inconsistency in LLM JSON output  
- No retry/validation layer yet  
- Stateless agent (no conversation memory)  

---

## 🚀 Next Steps
- Add JSON validation + retry mechanism  
- Improve prompt robustness for consistent multi-step reasoning  
- Add conversation memory  
- Improve response formatting (human-friendly output)  
- Build frontend (React + Redux)  
- Deploy as production-ready system  

---

## 🧠 Key Highlights
- Designed a **production-style AI agent architecture**  
- Implemented **multi-step reasoning with tool chaining**  
- Built **end-to-end system: User → LLM → Tools → Database**  
- Focused on **real-world CRM workflows and scalability**  

---

## 📌 Tech Stack
- Backend: FastAPI, SQLAlchemy  
- AI/LLM: Groq, LangChain  
- Agent Framework: LangGraph  
- Database: SQLite (can be extended to Postgres)  
