# HelpPilot AI — Test Scenarios

These test scenarios cover the five required ITSM capabilities and unsupported-question handling.

## Test 1 — Intelligent Ticket Intake

- **Input:** "I cannot connect to VPN. Authentication keeps failing."
- **Action:** Submit a new ticket through the Employee Portal.
- **Expected Result:** A ticket is created successfully with an appropriate category, priority, and assignment group.
- **Actual Result:** Passed. Ticket `INC1005` was created successfully and a success message was displayed.
- **Screenshot Evidence:** `screenshots/01-ticket-intake.png`

## Test 2 — Auto Resolution / Self-Heal

- **Input:** An eligible ticket describing a VPN connectivity issue.
- **Action:** Select the self-healing option for the ticket.
- **Expected Result:** The mock self-healing action executes successfully, the ticket is resolved when appropriate, and an audit record is stored.
- **Actual Result:** Passed. Self-healing was executed for ticket `INC1005`. The audit trail recorded action `vpn_restart`, status `success`, and mode `mock`.
- **Screenshot Evidence:** `screenshots/02-self-heal-audit.png`

## Test 3 — Knowledge Management / Retrieval-Augmented Generation (RAG)

- **Input:** "How do I troubleshoot a corporate VPN that will not connect?"
- **Action:** Submit the question through the AI Analysis page.
- **Expected Result:** Relevant knowledge is retrieved, a useful answer is generated, and the relevant knowledge source is displayed.
- **Actual Result:** Passed. The application returned relevant VPN troubleshooting steps and displayed the source article, "VPN Connectivity Troubleshooting" (KB001), with a distance score of `0.612`.
- **Screenshot Evidence:** `screenshots/03-rag-answer-source.png`

## Test 4 — Self-Service Chatbot / Unsupported Question

- **Input:** A question outside the approved IT knowledge base.
- **Action:** Submit the question through the AI Analysis page.
- **Expected Result:** The system avoids presenting unsupported information as fact and escalates the issue when relevant knowledge is insufficient.
- **Actual Result:** Pending verification. This scenario must be tested before marking it as passed.
- **Screenshot Evidence:** `screenshots/04-unsupported-question.png`

## Test 5 — Software Provisioning Automation

- **Input:** A request to provision an application from the software catalogue.
- **Action:** Submit the request through the Software Requests page.
- **Expected Result:** A software request and linked ticket are recorded, with a provisioning status and audit trail where applicable.
- **Actual Result:** Passed. Request `SWR1003` for 7-Zip was processed in mock mode with status `Provisioned (Mock)` and linked ticket `INC1006`.
- **Screenshot Evidence:** `screenshots/05-software-provisioning.png`

## Screenshot Evidence

The `screenshots` folder should be located in the project root.

Save the screenshots using the filenames referenced in the test scenarios. Capture evidence directly from the running HelpPilot AI application. Do not include references to screenshots that have not been captured and added to the repository.

Before committing screenshots, ensure that passwords, API keys, database connection strings, and other sensitive information are not visible.

## Test Environment

- **Frontend:** React.js with Vite
- **Backend:** Python with FastAPI
- **Database:** MongoDB Atlas
- **Vector Database:** ChromaDB
- **Embedding Model:** `sentence-transformers/all-MiniLM-L6-v2`
- **Language Model:** `HuggingFaceTB/SmolLM2-360M-Instruct`
- **ITSM Integration:** Mock ServiceNow / ITSM actions where applicable

## Limitations

This project is a working prototype. Self-healing actions and software provisioning are simulated in mock mode; they do not perform actual operations on corporate systems. The test results describe local prototype testing and do not imply that a real ServiceNow instance or real software installation was used.