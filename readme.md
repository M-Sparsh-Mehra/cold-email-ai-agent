# Local Agentic AI Job Outreach Pipeline

An automated, zero-cost, fully local AI agent pipeline that **parses resume**, **researches target companies**, **identifies HR contacts**, and **drafts highly personalized cold outreach emails** based on your professional profile.

Built with low-compute environments in mind, this project uses heavily quantized local LLMs and free search tools to completely bypass paid API limits and expensive hardware requirements.

---

## ✨ Key Features

- **100% Local & Free**  
  Powered by Ollama running a 4-bit quantized model (Phi-3 or Llama-3-8B) on CPU RAM.  
  No OpenAI API keys required.

- **Resume Parser (Resume-to-JSON)**

  Drag and drop your PDF resume into the **Identity Vault**. The system uses a local LLM pass to distill raw text into a structured JSON profile, ensuring the agents always speak in your specific professional voice.  

- **Resilient Web Scraping**  
  Uses DuckDuckGo Search (`ddgs`) and Jina Reader (`r.jina.ai`) to bypass bot protections and read web pages in clean, LLM-native Markdown.

- **Config-Driven Architecture**  
  Companies and user profiles are managed dynamically via `.yaml` files.  
  No hardcoded variables.

- **Fault-Tolerant State Tracking**  
  Uses a local SQLite database (`database.db`) to track pipeline states  
  (`Pending`, `Researched`, `Draft Created`).  
  If the script stops, it picks up right where it left off.

---

## 🧠 System Architecture & Data Flow

The pipeline operates in four distinct phases:

### 1. Ingestion Phase (`configs/`)
- The system reads your master `profile.yaml` (skills, tone, experience)
- Pulls target companies from `targets.yaml`

### 2. Research Phase (Agent 1)
- Queries the web for the target company's HR, Talent Acquisition, or recruiter contacts
- Scrapes the top result using **Jina Reader**
- Passes the markdown to the local LLM using **JSON Mode** to extract:
  - HR Name
  - Email
  - Context notes

### 3. Drafting Phase (Agent 2)
- Cross-references the scraped company context with `profile.yaml`
- Drafts a highly specific, context-aware cold email
- Highlights overlapping technologies  
  (e.g., matching your MoE pipeline work to their AI stack)

### 4. Storage Phase (`db_manager.py`)
- Saves the final subject line and email body to the local SQLite database
- Drafts are stored for later review and iteration

---

## 📂 Project Structure

```plaintext
job_agent_pipeline/
│
├── configs/                 # ⚙️ Configuration hub
│   ├── settings.yaml        # LLM parameters (model, temperature)
│   ├── targets.yaml         # List of companies to target
│   └── profile.yaml         # Your resume / skills context filled by Resume parser
│
├── src/                     # 🧠 Core logic
│   ├── agents/
│   │   ├── researcher.py    # Agent 1: Web search & JSON extraction
│   │   └── writer.py        # Agent 2: Synthesis & email drafting
│   ├── tools/
│   │   ├── search.py        # DuckDuckGo API & Jina Reader integration
|   |   ├──resume_parser.py  # Parses inputed resume and returns out in Json format to later give to llm
|   |   └── gmail_api.py        
│   └── db_manager.py        # SQLite operations & state tracking
│
├── main.py                  # 🚀 Master orchestrator
├── app.py                   # main app (RUN THIS!)
├── view_drafts.py           # 📊 CLI utility to view generated drafts
└── requirements.txt         # 📦 Python dependencies
```
## 🚧 Engineering Nuances & Bottlenecks

### The "JSON Delimiter" Challenge
**Issue:** Local LLMs are often non-deterministic and can return malformed JSON (e.g., raw newlines or missing commas).

**Solution:** Implemented a custom **Regex Sanitization Layer** and used **Strict JSON Mode** to validate and clean LLM responses before they hit the database.

### LinkedIn Defensive Bypassing
**Issue:** Direct scraping of LinkedIn triggers 403 errors and bot detection.

**Solution:** Pivoted to a **Search-Engine-Dorking** strategy, leveraging public indices to find leads without triggering platform-level defenses.

### State Persistence in Async Environments
**Issue:** FastAPI's async nature can lead to race conditions when multiple agents try to update the SQLite database.

**Solution:** Implemented a **Thread-Safe Database Manager** and used stateless agent transitions to ensure data integrity during deep-research sequences.

## 🛠️ Installation & Setup

### 1. Prerequisites
- **Python 3.10+**
- **Ollama** — download and install from https://ollama.com

---

### 2. Download the Local LLM

Ensure Ollama is running in the background, then pull a quantized model:

```bash
ollama pull phi3
```

### 3. Installation
```bash
git clone https://github.com/M-Sparsh-Mehra/cold-email-ai-agent.git

pip install -r requirements.txt
```

### 4. Execution
```bash
python app.py
```

Developed by: M Sparsh Mehra