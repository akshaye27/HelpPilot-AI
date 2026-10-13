# HelpPilot AI — Test Scenarios

These scenarios cover the five required ITSM capabilities and unsupported-question handling.

## Test 1 — Intelligent Ticket Intake
- Input: "I cannot connect to VPN. Authentication keeps failing."
- Action: Submit through the Employee Portal.
- Expected: A ticket is created with an appropriate category, priority, and assignment group.
- Actual result: Passed in local testing.

## Test 2 — Auto Resolution / Self-Heal
- Input: An eligible ticket describing a locked account or password issue.
- Action: Run the self-healing option.
- Expected: The mock action is executed, the ticket status is updated when successful, and an audit record is stored.
- Actual result: Passed in local testing.

## Test 3 — Knowledge Management / RAG
- Input: "How do I troubleshoot VPN connectivity?"
- Action: Submit the question through AI Analysis.
- Expected: Relevant knowledge is retrieved, a grounded answer is returned, and sources are displayed.
- Actual result: Passed in local testing.

## Test 4 — Self-Service Chatbot / Unsupported Question
- Input: A question outside the approved IT knowledge base.
- Action: Submit the question through AI Analysis.
- Expected: The system avoids presenting an unsupported answer as fact and escalates when relevant knowledge is insufficient.
- Actual result: Passed in local testing.

## Test 5 — Software Provisioning Automation
- Input: A request to provision Visual Studio Code.
- Action: Submit the request through Software Requests.
- Expected: A software request and linked ticket are recorded, with a mock provisioning status and audit trail.
- Actual result: Passed in local testing.

## Test environment
- Frontend: React with Vite
- Backend: Python with FastAPI
- Database: MongoDB Atlas
- Vector database: ChromaDB
- Embeddings: sentence-transformers/all-MiniLM-L6-v2
- Language model: HuggingFaceTB/SmolLM2-360M-Instruct
- Integration: Mock ServiceNow / ITSM actions where applicable

Note: This file documents the local prototype tests. It does not claim that real ServiceNow instances or real software installations were used.
