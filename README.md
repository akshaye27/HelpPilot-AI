# HelpPilot AI — Intelligent ITSM Helpdesk Automation

## 1. About the Project

HelpPilot AI is a prototype of an AI-powered IT helpdesk. It helps employees report technical problems, find solutions from a knowledge base, request software, and automate selected support tasks.

This project was developed as part of the AI-Powered ITSM Helpdesk Automation Technical Assessment.

## 2. Main Features

- **Intelligent Ticket Intake:** Employees can report IT problems through the application, and support tickets can be created and stored.
- **Auto Resolution and Self-Healing:** Selected support actions can be simulated for eligible account or VPN issues.
- **Knowledge Management and RAG:** The application searches IT support articles and uses relevant information to help answer questions.
- **Employee Self-Service and AI Chatbot:** Employees can ask questions and receive knowledge-based answers. Unsupported questions can be escalated.
- **Software Provisioning:** Employees can request software. The prototype records requests and simulates provisioning; it does not install software on real devices.
- **Audit Logs:** Supported actions can be recorded for review.

## 3. Technology Stack

| Component | Technology |
|---|---|
| Frontend | React.js with Vite |
| Backend | Python with FastAPI |
| Main database | MongoDB Atlas |
| Vector database | ChromaDB |
| Embedding model | sentence-transformers/all-MiniLM-L6-v2 |
| Language model | HuggingFaceTB/SmolLM2-360M-Instruct |
| ITSM integration | Mock ServiceNow-style actions |

## 4. How It Works

1. An employee submits a ticket or asks a question.
2. The React frontend sends the request to the FastAPI backend.
3. The backend processes the request and accesses MongoDB when required.
4. For knowledge questions, the system searches ChromaDB for relevant information.
5. The language model uses retrieved information to help generate an answer.
6. The application displays the result.
7. Supported automated actions can be recorded in audit logs.

## 5. Project Structure

- `frontend/` — React user interface.
- `backend/` — FastAPI application and Python scripts.
- `knowledge_base/` — Sample IT support documents.
- `tests/` — Test scenarios.
- `.gitignore` — Excludes local dependencies, generated files, and secrets from Git.
- `README.md` — Project documentation.

The local ChromaDB data is excluded from Git and can be rebuilt using the indexing scripts.

## 6. Requirements

You need:

- Python 3.12 or a compatible version.
- Node.js and npm.
- Git.
- A MongoDB Atlas database and its connection details.
- Internet access to download dependencies and AI models when required.

## 7. Setup and Installation

### Step 1: Clone the repository

Replace the placeholder with your GitHub repository URL.

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd HelpPilot-AI
```

### Step 2: Configure the backend

Open a terminal in the project folder and run:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Configure the required environment variables in your local `.env` file. Make sure the backend has access to your MongoDB Atlas database.

Install the Python dependencies using the dependency file included in the project.

**Security:** Never upload your `.env` file, passwords, database connection strings, or API keys to GitHub.

### Step 3: Start the backend

From the `backend` directory, run:

```powershell
python -m uvicorn main:app --reload
```

The backend should be available at:

- API: http://127.0.0.1:8000
- Interactive API documentation: http://127.0.0.1:8000/docs

Keep this terminal running.

### Step 4: Start the frontend

Open a second terminal and run:

```powershell
cd "$HOME\Desktop\ITSM Help Desk\frontend"
npm install
npm run dev
```

Open the local URL displayed in the terminal, normally http://localhost:5173.

Keep both the frontend and backend running while using the application.

### Step 5: Prepare the knowledge base

Use the project's knowledge preparation and indexing scripts from the backend directory. Install the required dependencies and configure the environment before running them.

The ChromaDB vector database must be populated before testing knowledge retrieval.

## 8. API Documentation

The backend provides the following endpoints.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | Backend root endpoint |
| GET | `/api/tickets` | Retrieve tickets |
| POST | `/api/tickets` | Create a ticket |
| POST | `/api/self-heal` | Run a supported self-healing action |
| GET | `/api/software/catalogue` | Retrieve the software catalogue |
| POST | `/api/software/requests` | Submit a software request |
| GET | `/api/software/requests` | Retrieve software requests |
| GET | `/api/knowledge/articles` | Retrieve knowledge articles |
| POST | `/api/knowledge/search` | Search the knowledge base |
| POST | `/api/knowledge/answer` | Generate an answer using knowledge retrieval |
| GET | `/api/audit` | Retrieve audit records |

Visit http://127.0.0.1:8000/docs to inspect and test the API endpoints.

## 9. Database Design

MongoDB Atlas stores the application's main records in collections including:

- `tickets` — Support tickets.
- `knowledge` — Knowledge articles.
- `chat` — Chat-related records.
- `audit` — Records of supported actions.
- `counters` — Counter or sequence data.
- `software_requests` — Software requests.

ChromaDB stores vector representations of knowledge chunks. These help the application find information related to a question, even when the wording differs from the original article.

## 10. AI and RAG Approach

RAG stands for Retrieval-Augmented Generation.

The process works as follows:

1. Prepare IT support documents.
2. Split documents into smaller text chunks.
3. Convert the chunks into numerical representations called embeddings.
4. Store the vectors in ChromaDB.
5. Search for information relevant to the employee's question.
6. Use the retrieved information with the language model to generate an answer.
7. Escalate when the available information is insufficient.

This approach helps connect answers to the available knowledge base.

## 11. ServiceNow Integration

The current prototype uses mock ITSM actions to demonstrate the intended integration workflow.

It demonstrates ticket handling, selected automated actions, software request processing, and audit logging without requiring a live ServiceNow instance.

**Limitation:** The application is not connected to a real ServiceNow instance. Software provisioning is simulated and does not install software on employee devices.

## 12. Testing

The test scenarios are documented in `tests/TEST_SCENARIOS.md`.

The main scenarios cover:

1. Creating an IT support ticket.
2. Running an eligible self-healing action.
3. Finding relevant information for VPN or Outlook questions.
4. Escalating a question that is not sufficiently supported by the knowledge base.
5. Submitting a software provisioning request.

The project has been tested locally during development. See the test scenario document for the recorded results.

## 13. Security and Limitations

- Store private credentials in a local `.env` file.
- Never commit passwords, database connection strings, or API keys to Git.
- The application requires access to the configured MongoDB Atlas database.
- ChromaDB may need to be rebuilt if its local data is removed.
- AI responses depend on the retrieved information and the language model.
- Self-healing and software provisioning actions are simulations.
- Production use would require additional security, authentication, testing, and real ITSM integration.

## 14. Future Improvements

Possible improvements include:

- Connecting to a real ServiceNow instance.
- Adding user authentication and role-based access.
- Improving ticket classification and assignment.
- Adding more knowledge articles and test cases.
- Expanding automated troubleshooting with appropriate approval checks.
- Deploying the application to a secure hosting environment.

## 15. Conclusion

HelpPilot AI demonstrates how a web application, database, language model, and vector search can work together to support common IT helpdesk tasks.

The prototype covers ticket intake, knowledge-based answers, selected self-healing actions, software requests, and audit logging. It also demonstrates how unsupported questions and simulated integrations can be handled transparently.