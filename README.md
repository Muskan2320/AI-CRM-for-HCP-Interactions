# 🚀 AI CRM for HCP Interactions (Current Progress)

This project is an AI-first CRM system designed for managing interactions with Healthcare Professionals (HCPs). It enables structured logging, intelligent updates, and AI-powered workflows using LangGraph and LLMs.

---

## 🎯 Problem Statement

The goal is to build a CRM system that allows field representatives to efficiently log, track, and manage interactions with healthcare professionals. The system should support both structured data entry and AI-assisted workflows to improve productivity, data consistency, and follow-up tracking.

---

## ⚙️ Features Implemented

### 1. HCP Management
- Dynamic creation of HCP records during interaction logging  
- Search-first approach to avoid duplicate entries  
- Auto-update of missing HCP fields (e.g., specialization, city)  

### 2. Interaction Logging
- Log interactions with structured data:
  - Doctor name, hospital  
  - Topic, notes  
  - Follow-up details  
- Intelligent follow-up status handling:
  - `pending` (when follow-up exists)  
  - `no_follow_up` (when no follow-up required)  

### 3. Follow-up Status Standardization
- Controlled values:
  - `pending`, `completed`, `cancelled`, `no_follow_up`  
- Ensures data consistency and reliable filtering  

### 4. Interaction Update (Edit Feature)
- Update existing interaction details:
  - Follow-up status, notes, topic, follow-up date/action  
- Returns structured response with updated fields  

### 5. HCP Search API
- Search by:
  - HCP ID (highest priority)  
  - Name  
  - Hospital  
- Default: returns latest 10 HCP records  

### 6. AI Integration
- Integrated Groq LLM (`llama-3.3-70b-versatile`) via LangChain  
- Verified end-to-end LLM response pipeline  

### 7. LangGraph Tools
- `SearchHCPTool` – fetch HCP details  
- `LogInteractionTool` – log interaction into CRM  
- `EditInteractionTool` – update existing interaction  

---

## 🚧 Next Steps

- Implement `GetPendingFollowupsTool`  
- Implement `GetHCPInteractionsTool`  
- Build full LangGraph agent (decision-making flow)  
- Add conversational chat-based interaction logging  
- Develop frontend (React + Redux)  