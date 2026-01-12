
# data-intake-chatops

## Overview

**data-intake-chatops** is a conversational ChatOps system designed to simplify and standardize data platform intake workflows. Instead of manually creating configuration files, users interact with a chatbot that guides them through a structured intake conversation. The chatbot collects required metadata, converts it into a YAML configuration, and automatically raises a GitHub Pull Request following GitOps best practices.

This project is intentionally scoped as an **MVP / POC** and focuses only on:

* Conversational intake
* Structured metadata collection
* YAML generation
* Automated Pull Request creation

> 🚫 No AWS provisioning is performed in this project.

---

## Why This Project Exists

Data platform onboarding often suffers from:

* Manual YAML/JSON editing
* Missing or inconsistent metadata
* Naming convention violations
* Back-and-forth reviews

This project demonstrates how **AI + ChatOps + GitOps** can:

* Enforce structured intake through conversation
* Reduce human error
* Improve developer experience
* Standardize data onboarding workflows

---

## Key Capabilities

* 🤖 **Conversational Intake**
  A Gemini-powered chatbot asks one question at a time and guides users through required metadata fields.
* 🧠 **Stateful Sessions**
  The chatbot remembers previous answers and only asks for missing information.
* 📄 **YAML Configuration Generation**
  User responses are converted into a clean, human-readable YAML config.
* 🔁 **GitOps Automation**
  The system creates a feature branch, commits the YAML file, and raises a Pull Request to the `dev` branch.

---

## High-Level Arc# data-intake-chatops

## Overview

**data-intake-chatops** is a conversational ChatOps system designed to simplify and standardize data platform intake workflows. Instead of manually creating configuration files, users interact with a chatbot that guides them through a structured intake conversation. The chatbot collects required metadata, converts it into a YAML configuration, and automatically raises a GitHub Pull Request following GitOps best practices.

This project is intentionally scoped as an **MVP / POC** and focuses only on:

* Conversational intake
* Structured metadata collection
* YAML generation
* Automated Pull Request creation

> 🚫 No AWS provisioning is performed in this project.

---

## Why This Project Exists

Data platform onboarding often suffers from:

* Manual YAML/JSON editing
* Missing or inconsistent metadata
* Naming convention violations
* Back-and-forth reviews

This project demonstrates how **AI + ChatOps + GitOps** can:

* Enforce structured intake through conversation
* Reduce human error
* Improve developer experience
* Standardize data onboarding workflows

---

## Key Capabilities

* 🤖 **Conversational Intake**
  A Gemini-powered chatbot asks one question at a time and guides users through required metadata fields.

* 🧠 **Stateful Sessions**
  The chatbot remembers previous answers and only asks for missing information.

* 📄 **YAML Configuration Generation**
  User responses are converted into a clean, human-readable YAML config.

* 🔁 **GitOps Automation**
  The system creates a feature branch, commits the YAML file, and raises a Pull Request to the `dev` branch.

---

## High-Level Architecture

```
User (CLI / UI / API)
        │
        ▼
Conversation Engine (Gemini)
        │
        ▼
Intake State Manager
        │
        ▼
YAML Generator
        │
        ▼
GitHub Branch + Pull Request
```

---

## Tech Stack

| Layer          | Technology                    |
| -------------- | ----------------------------- |
| Language       | Python 3.10+                  |
| LLM            | Google Gemini (via LangChain) |
| API Framework  | FastAPI (optional for MVP)    |
| YAML Handling  | PyYAML                        |
| Git Automation | GitPython                     |
| PR Creation    | GitHub REST API               |

---

## Project Structure

```
data-intake-chatops/
│
├── app/
│   ├── main.py               # Application entry point
│   ├── chatbot.py            # Gemini LLM interaction
│   ├── intake_flow.py        # Intake questions & state management
│   ├── yaml_generator.py     # YAML creation logic
│   ├── git_ops.py            # Git branch & PR automation
│
├── sessions/                 # Stored session state (MVP)
├── requirements.txt
└── README.md
```

---

## Intake Fields (MVP Scope)

The chatbot currently collects the following required fields:

* `intake_id`
* `database_name`
* `database_s3_location`
* `database_description`
* `aws_account_id`
* `region`
* `data_construct`
* `data_env`
* `data_layer`
* `source_name`
* `enterprise_or_func_name`
* `enterprise_or_func_subgrp_name`

> ⚠️ Validation rules and naming conventions are intentionally **out of scope** for this MVP and will be added later.

---

## Example Generated YAML

```yaml
intake_id: M0000562
database_name: minerva_dev_src_corp_gtc_cdp_sap_gtc_prd_raw_db
database_s3_location: s3://minerva-dev-src-corp-gtc/cdp/prd/raw/sap_gtc/
database_description: Used to store raw tables for sap_gtc
aws_account_id: "438465132548"
region: us-east-1
data_construct: Source
data_env: prd
data_layer: raw
source_name: SAP_GTC
enterprise_or_func_name: CORP
enterprise_or_func_subgrp_name: GTC
```

---

## How the Flow Works (Step-by-Step)

1. User starts a chatbot session
2. Bot asks for required fields one at a time
3. Answers are stored in session state
4. Once all fields are collected:

   * YAML file is generated
   * Feature branch is created
   * YAML is committed
   * Pull Request is raised to `dev`

---

## Running the Project (MVP)

### 1. Clone the Repository

```bash
git clone <repo-url>
cd data-intake-chatops
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Environment Variables

```bash
export GOOGLE_API_KEY="your-gemini-api-key"
export GITHUB_TOKEN="your-github-token"
```

### 5. Run the Application

```bash
python app/main.py
```

---

## What This MVP Does NOT Do

* ❌ No AWS resource provisioning
* ❌ No policy validation (yet)
* ❌ No approval workflows
* ❌ No UI beyond CLI / API

These are deliberate design choices to keep the POC focused and demo-ready.

---

## Future Enhancements

* Naming convention validation
* Regex-based rule enforcement
* Policy-as-code (OPA / JSON Schema)
* Slack / MS Teams bot integration
* Web UI
* Approval comments and reviewers
* AWS provisioning via Terraform

---

## Demo Pitch (One-Liner)

> "This project shows how conversational AI can replace manual data intake forms by turning human input into governed, GitOps-ready YAML and automated pull requests."

---

## License

Internal / POC
hitecture

```
User (CLI / UI / API)
        │
        ▼
Conversation Engine (Gemini)
        │
        ▼
Intake State Manager
        │
        ▼
YAML Generator
        │
        ▼
GitHub Branch + Pull Request
```

---

## Tech Stack

| Layer          | Technology                    |
| -------------- | ----------------------------- |
| Language       | Python 3.10+                  |
| LLM            | Google Gemini (via LangChain) |
| API Framework  | FastAPI (optional for MVP)    |
| YAML Handling  | PyYAML                        |
| Git Automation | GitPython                     |
| PR Creation    | GitHub REST API               |

---

## Project Structure

```
data-intake-chatops/
│
├── app/
│   ├── main.py               # Application entry point
│   ├── chatbot.py            # Gemini LLM interaction
│   ├── intake_flow.py        # Intake questions & state management
│   ├── yaml_generator.py     # YAML creation logic
│   ├── git_ops.py            # Git branch & PR automation
│
├── sessions/                 # Stored session state (MVP)
├── requirements.txt
└── README.md
```

---

## Intake Fields (MVP Scope)

The chatbot currently collects the following required fields:

* `intake_id`
* `database_name`
* `database_s3_location`
* `database_description`
* `aws_account_id`
* `region`
* `data_construct`
* `data_env`
* `data_layer`
* `source_name`
* `enterprise_or_func_name`
* `enterprise_or_func_subgrp_name`

> ⚠️ Validation rules and naming conventions are intentionally **out of scope** for this MVP and will be added later.

---

## Example Generated YAML

```yaml
intake_id: M0000562
database_name: minerva_dev_src_corp_gtc_cdp_sap_gtc_prd_raw_db
database_s3_location: s3://minerva-dev-src-corp-gtc/cdp/prd/raw/sap_gtc/
database_description: Used to store raw tables for sap_gtc
aws_account_id: "438465132548"
region: us-east-1
data_construct: Source
data_env: prd
data_layer: raw
source_name: SAP_GTC
enterprise_or_func_name: CORP
enterprise_or_func_subgrp_name: GTC
```

---

## How the Flow Works (Step-by-Step)

1. User starts a chatbot session
2. Bot asks for required fields one at a time
3. Answers are stored in session state
4. Once all fields are collected:

   * YAML file is generated
   * Feature branch is created
   * YAML is committed
   * Pull Request is raised to `dev`

---

## Running the Project (MVP)

### 1. Clone the Repository

```bash
git clone <repo-url>
cd data-intake-chatops
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Environment Variables

```bash
export GOOGLE_API_KEY="your-gemini-api-key"
export GITHUB_TOKEN="your-github-token"
```

### 5. Run the Application

```bash
python app/main.py
```

---

### 6. Run the Application backend

```bash
uvicorn app.api:app --reload
```

## What This MVP Does NOT Do

* ❌ No AWS resource provisioning
* ❌ No policy validation (yet)
* ❌ No approval workflows
* ❌ No UI beyond CLI / API

These are deliberate design choices to keep the POC focused and demo-ready.

---

## Future Enhancements

* Naming convention validation
* Regex-based rule enforcement
* Policy-as-code (OPA / JSON Schema)
* Slack / MS Teams bot integration
* Web UI
* Approval comments and reviewers
* AWS provisioning via Terraform

---

## Demo Pitch (One-Liner)

> "This project shows how conversational AI can replace manual data intake forms by turning human input into governed, GitOps-ready YAML and automated pull requests."

---

## License

Internal / POC