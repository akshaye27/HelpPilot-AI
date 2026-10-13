

import os

import re

from contextlib import asynccontextmanager

from datetime import datetime, timezone

from threading import Lock



import chromadb

import torch

from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException

from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel

from pymongo import MongoClient, DESCENDING, ReturnDocument

from pymongo.errors import PyMongoError

from sentence_transformers import SentenceTransformer

from transformers import AutoTokenizer, AutoModelForCausalLM





# ============================================================

# 1. ENVIRONMENT SETTINGS

# ============================================================



load_dotenv()



MONGODB_URI = os.getenv("MONGODB_URI")

MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "helppilot")



if not MONGODB_URI:

    raise ValueError("MONGODB_URI is missing from the .env file.")



LLM_MODEL_NAME = "HuggingFaceTB/SmolLM2-360M-Instruct"

RETRIEVAL_DISTANCE_THRESHOLD = 1.15





# ============================================================

# 2. MONGODB CONNECTION AND COLLECTIONS

# ============================================================



client = MongoClient(

    MONGODB_URI,

    serverSelectionTimeoutMS=10000,

)



db = client[MONGODB_DATABASE]



tickets_collection = db["tickets"]

knowledge_mongo_collection = db["knowledge"]

chat_collection = db["chat"]

audit_collection = db["audit"]

counters_collection = db["counters"]
software_requests_collection = db["software_requests"]





# ============================================================

# 3. CHROMADB AND EMBEDDING MODEL

# ============================================================



CHROMA_PATH = os.path.join(

    os.path.dirname(os.path.abspath(__file__)),

    "chroma_db",

)



chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)



knowledge_collection = chroma_client.get_collection(

    name="helpdesk_knowledge"

)



embedding_model = SentenceTransformer(

    "sentence-transformers/all-MiniLM-L6-v2"

)





# ============================================================

# 4. LOAD THE LLM WHEN FASTAPI STARTS

# ============================================================



llm_tokenizer = None

llm_model = None

llm_lock = Lock()





@asynccontextmanager

async def lifespan(app: FastAPI):

    global llm_tokenizer, llm_model



    print("Checking MongoDB Atlas connection...")

    client.admin.command("ping")

    print("MongoDB Atlas connected.")



    print("Loading SmolLM2 tokenizer...")

    llm_tokenizer = AutoTokenizer.from_pretrained(LLM_MODEL_NAME)



    print("Loading SmolLM2-360M-Instruct...")

    llm_model = AutoModelForCausalLM.from_pretrained(

        LLM_MODEL_NAME,

        dtype=torch.float32,

        low_cpu_mem_usage=True,

    )



    llm_model.eval()

    print("HelpPilot AI LLM loaded successfully.")



    yield



    llm_model = None

    llm_tokenizer = None

    client.close()



    print("HelpPilot AI backend shut down.")





# ============================================================

# 5. FASTAPI INITIALISATION

# ============================================================



app = FastAPI(

    title="HelpPilot AI - ITSM Help Desk API",

    description=(

        "IT service desk with ticket classification, "

        "RAG-based support, mock self-healing, and audit logging."

    ),

    version="1.2.0",

    lifespan=lifespan,

)



app.add_middleware(

    CORSMiddleware,

    allow_origins=[

        "http://localhost:5173",

        "http://127.0.0.1:5173",

    ],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],

)





# ============================================================

# 6. REQUEST MODELS AND INDEXES

# ============================================================



class KnowledgeSearchRequest(BaseModel):

    question: str





class SelfHealRequest(BaseModel):

    ticket_id: str

    action: str = "account_unlock"


class SoftwareProvisionRequest(BaseModel):

    software_name: str

    justification: str

    requested_by: str





tickets_collection.create_index(

    [("ticket_id", DESCENDING)],

    unique=True,

)



tickets_collection.create_index(

    [("created_at", DESCENDING)],

)



audit_collection.create_index(

    [("created_at", DESCENDING)],

)





# ============================================================

# 7. RULE-BASED TICKET CLASSIFICATION

# ============================================================



def classify_request(message):

    text = message.lower()



    
    if any(word in text for word in [
        "vpn", "wifi", "wi-fi", "network", "internet"
    ]):
        return {
            "intent": "Incident",
            "category": "Network",
            "subcategory": "VPN",
            "priority": "P2",
            "impact": "Individual",
            "urgency": "High",
            "assignment_group": "Network Support",
            "summary": "VPN authentication failure",
            "resolution": (
                "Follow the approved VPN troubleshooting guide. "
                "Check network connectivity and VPN authentication. "
                "Escalate to Network Support if the issue persists."
            ),
            "confidence": 0.90,
        }




    if any(word in text for word in [

        "password",
        "locked out",
        "account unlock",
        "account is locked",
        "account locked",
        "unlock my account",
        "unlock account",
        "cannot sign in",
        "can't sign in",
        "unable to sign in",
        "cannot log in",
        "can't log in",
        "unable to log in"

    ]):

        return {

            "intent": "Automatable Issue",

            "category": "Access",

            "subcategory": "Password / Account",

            "priority": "P2",

            "assignment_group": "IT Support",

            "summary": "Password or account access issue",

            "resolution": (

                "Verify the user's identity and follow the "

                "approved password reset procedure."

            ),

            "confidence": 0.90,

        }



    if any(word in text for word in [

        "install", "software", "visual studio code", "vscode"

    ]):

        return {

            "intent": "Service Request",

            "category": "Software",

            "subcategory": "Software Installation",

            "priority": "P3",

            "assignment_group": "Software Support",

            "summary": "Software installation request",

            "resolution": (

                "Check the software catalogue and submit "

                "a provisioning request."

            ),

            "confidence": 0.90,

        }



    if any(word in text for word in [

        "outlook", "synchronization", "sync", "email"

    ]):

        return {

            "intent": "Knowledge Question",

            "category": "Application",

            "subcategory": "Outlook",

            "priority": "P3",

            "assignment_group": "IT Support",

            "summary": "Outlook support question",

            "resolution": (

                "Search the approved Outlook troubleshooting "

                "knowledge articles."

            ),

            "confidence": 0.85,

        }



    return {

        "intent": "Unknown",

        "category": "Unclassified",

        "subcategory": "Unknown",

        "priority": "Unassigned",

        "assignment_group": "Helpdesk",

        "summary": "Request needs further investigation",

        "resolution": (

            "The system could not confidently classify this "

            "request. Escalate it to human support."

        ),

        "confidence": 0.30,

    }





# ============================================================

# 8. HELPER FUNCTIONS

# ============================================================



def generate_ticket_id():

    counter = counters_collection.find_one_and_update(

        {"_id": "ticket_id"},

        {

            "$inc": {"sequence": 1},

            "$setOnInsert": {"starting_sequence": 1000},

        },

        upsert=True,

        return_document=ReturnDocument.AFTER,

    )



    return f"INC{counter['sequence'] + 1000}"





def format_ticket(document):

    document["id"] = document.pop("ticket_id")

    document.pop("_id", None)

    return document





def write_audit_record(

    ticket_id,

    action,

    status,

    details,

):

    """Store a record of a simulated automated action."""

    audit_collection.insert_one({

        "ticket_id": ticket_id,

        "action": action,

        "status": status,

        "details": details,

        "execution_mode": "mock",

        "created_at": datetime.now(timezone.utc).isoformat(),

    })





# ============================================================

# 9. HEALTH CHECK

# ============================================================



@app.get("/")

def home():

    return {

        "message": "HelpPilot AI ITSM Help Desk backend is running",

        "llm_model": LLM_MODEL_NAME,

        "self_healing_mode": "mock",

    }





# ============================================================

# 10. GET TICKETS

# ============================================================



@app.get("/api/tickets")

def get_tickets():

    try:

        documents = tickets_collection.find().sort(

            "created_at",

            DESCENDING,

        )



        return {

            "tickets": [

                format_ticket(document)

                for document in documents

            ]

        }



    except PyMongoError as error:

        raise HTTPException(

            status_code=503,

            detail="Unable to retrieve tickets from the database.",

        ) from error





# ============================================================

# 11. CREATE AND CLASSIFY A TICKET

# ============================================================



@app.post("/api/tickets")

def create_ticket(ticket: dict):

    description = ticket.get("description", "")



    if not isinstance(description, str) or not description.strip():

        raise HTTPException(

            status_code=422,

            detail="Description is required.",

        )



    description = description.strip()

    analysis = classify_request(description)



    try:

        ticket_id = generate_ticket_id()



        new_ticket = {

            "ticket_id": ticket_id,

            "description": description,

            "created_at": datetime.now(timezone.utc).isoformat(),

            "status": "Open",

            **analysis,

        }



        tickets_collection.insert_one(new_ticket.copy())



        return {

            "message": "Ticket classified successfully",

            "ticket": format_ticket(new_ticket),

            "source": "FastAPI + MongoDB Atlas",

        }



    except PyMongoError as error:

        raise HTTPException(

            status_code=503,

            detail="Unable to save the ticket to the database.",

        ) from error





# ============================================================

# 12. MOCK SELF-HEALING AND AUDIT LOGGING

# ============================================================




@app.post("/api/self-heal")
def self_heal(request: SelfHealRequest):
    """
    Simulate an approved IT action.

    No real user account or corporate system is modified.
    The ticket is updated only after the mock action succeeds.
    """

    ticket_id = request.ticket_id.strip()
    action = request.action.strip().lower()

    if not ticket_id:
        raise HTTPException(
            status_code=422,
            detail="Ticket ID is required.",
        )

    allowed_actions = {
        "account_unlock": {
            "label": "Account unlock",
            "description": (
                "Simulated account unlock completed successfully."
            ),
        },
        "password_reset": {
            "label": "Password reset",
            "description": (
                "Simulated password reset workflow completed. "
                "No actual password was changed."
            ),
        },
        "vpn_restart": {
            "label": "VPN restart",
            "description": (
                "Simulated VPN client restart completed."
            ),
        },
        "clear_cache": {
            "label": "Cache clearing",
            "description": (
                "Simulated application cache clearing completed."
            ),
        },
        "application_restart": {
            "label": "Application restart",
            "description": (
                "Simulated application restart completed."
            ),
        },
    }

    if action not in allowed_actions:
        raise HTTPException(
            status_code=422,
            detail=(
                "Unsupported action. Choose account_unlock, "
                "password_reset, vpn_restart, clear_cache, "
                "or application_restart."
            ),
        )

    try:
        # Find the ticket using the ID field used by this application.
        ticket = tickets_collection.find_one({"id": ticket_id})

        # Support older records that may use ticket_id instead.
        if not ticket:
            ticket = tickets_collection.find_one(
                {"ticket_id": ticket_id}
            )

        if not ticket:
            raise HTTPException(
                status_code=404,
                detail=f"Ticket {ticket_id} was not found.",
            )

        # Identify the ticket's issue type.
        description = ticket.get("description", "").lower()
        category = ticket.get("category", "")
        subcategory = ticket.get("subcategory", "")

        # Check that the requested action matches the ticket.
        if action in ("account_unlock", "password_reset"):
            compatible = (
                category == "Access"
                or "password" in description
                or "locked out" in description
                or "account unlock" in description
                or "account is locked" in description
                or "password" in subcategory.lower()
            )

        elif action == "vpn_restart":
            compatible = (
                category == "Network"
                or "vpn" in description
            )

        else:
            compatible = (
                category in ("Application", "Software")
                or any(
                    word in description
                    for word in [
                        "application",
                        "outlook",
                        "software",
                        "cache",
                    ]
                )
            )

        if not compatible:
            details = (
                "Action rejected because it does not match "
                "the ticket's issue type."
            )

            write_audit_record(
                ticket_id,
                action,
                "rejected",
                details,
            )

            return {
                "ticket_id": ticket_id,
                "action": action,
                "status": "rejected",
                "ticket_status": ticket.get("status", "Open"),
                "message": details,
                "execution_mode": "mock",
            }

        # Do not execute an action on an already-resolved ticket.
        if str(ticket.get("status", "")).lower() == "resolved":
            details = (
                "Action not executed because the ticket "
                "is already resolved."
            )

            write_audit_record(
                ticket_id,
                action,
                "skipped",
                details,
            )

            return {
                "ticket_id": ticket_id,
                "action": action,
                "status": "skipped",
                "ticket_status": "Resolved",
                "message": details,
                "execution_mode": "mock",
            }

        # STEP 1: Identify.
        identified_issue = ticket.get(
            "summary",
            "IT support issue",
        )

        # STEP 2: Diagnose.
        diagnosis = (
            f"Ticket classified as {category} / {subcategory}."
        )

        # STEP 3: Search the approved knowledge base.
        knowledge_results = search_knowledge_chunks(
            ticket.get("description", "")
        )

        relevant_results = [
            result
            for result in knowledge_results
            if result["distance"] <= RETRIEVAL_DISTANCE_THRESHOLD
        ]

        knowledge_source = None

        if relevant_results:
            best_result = relevant_results[0]
            metadata = best_result.get("metadata", {})

            knowledge_source = {
                "title": metadata.get(
                    "title",
                    "Knowledge article",
                ),
                "document_id": metadata.get("document_id"),
                "distance": best_result["distance"],
            }

        # STEP 4: Escalate if approved knowledge is unavailable.
        if not knowledge_source:
            details = (
                "Self-healing stopped because no sufficiently "
                "relevant approved knowledge was found. "
                "Human support is required."
            )

            # Update the ticket before recording the escalation.
            ticket_filter = (
                {"id": ticket_id}
                if ticket.get("id") == ticket_id
                else {"ticket_id": ticket_id}
            )

            tickets_collection.update_one(
                ticket_filter,
                {
                    "$set": {
                        "status": "Open",
                        "resolution": details,
                        "resolution_type": "Human escalation",
                    }
                },
            )

            write_audit_record(
                ticket_id,
                action,
                "escalated",
                details,
            )

            return {
                "ticket_id": ticket_id,
                "action": action,
                "status": "escalated",
                "ticket_status": "Open",
                "message": details,
                "knowledge_source": None,
                "execution_mode": "mock",
            }

        # STEP 5: Execute the approved mock action.
        action_result = allowed_actions[action]

        validation = (
            "Mock validation successful. "
            "The simulated action completed successfully."
        )

        # STEP 6: Save the successful result to the ticket.
        ticket_filter = (
            {"id": ticket_id}
            if ticket.get("id") == ticket_id
            else {"ticket_id": ticket_id}
        )

        update_result = tickets_collection.update_one(
            ticket_filter,
            {
                "$set": {
                    "status": "Resolved",
                    "resolution": action_result["description"],
                    "resolution_type": "Mock self-healing",
                    "self_heal_action": action,
                    "self_heal_validation": validation,
                    "self_heal_knowledge_source": (
                        knowledge_source["title"]
                    ),
                }
            },
        )

        # Do not claim success if MongoDB did not update the ticket.
        if update_result.matched_count == 0:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Ticket {ticket_id} was not found during "
                    "the status update."
                ),
            )

        # STEP 7: Record the successful action in the audit log.
        details = (
            f"Issue: {identified_issue}. "
            f"Diagnosis: {diagnosis} "
            f"Knowledge source: {knowledge_source['title']}. "
            f"Action: {action_result['description']} "
            f"Validation: {validation}"
        )

        write_audit_record(
            ticket_id,
            action,
            "success",
            details,
        )

        return {
            "ticket_id": ticket_id,
            "issue": identified_issue,
            "diagnosis": diagnosis,
            "action": action,
            "action_label": action_result["label"],
            "status": "success",
            "ticket_status": "Resolved",
            "validation": validation,
            "message": action_result["description"],
            "execution_mode": "mock",
            "knowledge_source": knowledge_source,
        }

    except HTTPException:
        raise

    except PyMongoError as error:
        print(f"Self-healing database error: {error}")

        raise HTTPException(
            status_code=503,
            detail=(
                "The self-healing operation could not be "
                "completed because of a database error."
            ),
        ) from error





# ============================================================
# 13. SOFTWARE CATALOGUE AND MOCK PROVISIONING
# ============================================================

SOFTWARE_CATALOGUE = {
    "visual studio code": {
        "display_name": "Visual Studio Code",
        "publisher": "Microsoft",
        "category": "Development",
        "approval_required": True,
    },
    "7-zip": {
        "display_name": "7-Zip",
        "publisher": "7-Zip",
        "category": "Utilities",
        "approval_required": True,
    },
    "vlc media player": {
        "display_name": "VLC Media Player",
        "publisher": "VideoLAN",
        "category": "Media",
        "approval_required": True,
    },
    "notepad++": {
        "display_name": "Notepad++",
        "publisher": "Notepad++ Team",
        "category": "Utilities",
        "approval_required": True,
    },
    "zoom": {
        "display_name": "Zoom Workplace",
        "publisher": "Zoom",
        "category": "Communication",
        "approval_required": True,
    },
}


@app.get("/api/software/catalogue")
def get_software_catalogue():
    """Return the approved mock software catalogue."""
    return {
        "count": len(SOFTWARE_CATALOGUE),
        "software": list(SOFTWARE_CATALOGUE.values()),
        "execution_mode": "mock",
    }


@app.post("/api/software/requests")
def create_software_request(request: SoftwareProvisionRequest):
    """Create a software service request and simulate provisioning."""
    software_key = request.software_name.strip().lower()
    justification = request.justification.strip()
    requested_by = request.requested_by.strip()

    if not software_key:
        raise HTTPException(status_code=422, detail="Software name is required.")
    if not justification:
        raise HTTPException(status_code=422, detail="A business justification is required.")
    if not requested_by:
        raise HTTPException(status_code=422, detail="Requester name is required.")

    software = SOFTWARE_CATALOGUE.get(software_key)

    if not software:
        # Also allow an exact match against catalogue display names.
        software = next(
            (
                item
                for item in SOFTWARE_CATALOGUE.values()
                if item.get("display_name", "").strip().casefold()
                == software_key
            ),
            None,
        )

    if not software:
        raise HTTPException(
            status_code=422,
            detail=(
                "Software is not in the approved catalogue. "
                "Choose an item returned by GET /api/software/catalogue."
            ),
        )

    created_at = datetime.now(timezone.utc).isoformat()

    try:
        # Create the linked ITSM service-request ticket.
        ticket_id = generate_ticket_id()
        ticket_document = {
            "ticket_id": ticket_id,
            "description": (
                f"Software request: {software['display_name']}. "
                f"Justification: {justification}"
            ),
            "created_at": created_at,
            "status": "Open",
            "intent": "Service Request",
            "category": "Software",
            "subcategory": "Software Installation",
            "priority": "P3",
            "assignment_group": "Software Support",
            "summary": f"Software request - {software['display_name']}",
            "resolution": "Software request submitted for mock provisioning.",
            "confidence": 0.99,
        }
        tickets_collection.insert_one(ticket_document.copy())

        # Generate a separate software-request ID.
        request_counter = counters_collection.find_one_and_update(
            {"_id": "software_request_id"},
            {
                "$inc": {"sequence": 1},
                "$setOnInsert": {"starting_sequence": 1000},
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        request_id = f"SWR{request_counter['sequence'] + 1000}"

        request_document = {
            "request_id": request_id,
            "ticket_id": ticket_id,
            "software": software,
            "justification": justification,
            "requested_by": requested_by,
            "status": "Provisioned (Mock)",
            "approval_status": "Simulated approval",
            "provisioning_result": (
                "Mock provisioning completed successfully. "
                "No software was installed on a real device."
            ),
            "execution_mode": "mock",
            "created_at": created_at,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        software_requests_collection.insert_one(request_document.copy())

        tickets_collection.update_one(
            {"ticket_id": ticket_id},
            {
                "$set": {
                    "status": "Resolved",
                    "resolution": request_document["provisioning_result"],
                    "resolved_at": datetime.now(timezone.utc).isoformat(),
                    "resolution_type": "Mock software provisioning",
                    "software_request_id": request_id,
                }
            },
        )

        write_audit_record(
            ticket_id,
            "software_provisioning",
            "success",
            (
                f"Request {request_id} for {software['display_name']} "
                f"submitted by {requested_by}. "
                "Mock provisioning result: success; no real installation occurred."
            ),
        )

        return {
            "message": "Software request processed in mock mode.",
            "request": request_document,
            "ticket": {"id": ticket_id, "status": "Resolved"},
            "execution_mode": "mock",
        }

    except PyMongoError as error:
        print(f"Software provisioning database error: {error}")
        raise HTTPException(
            status_code=503,
            detail=(
                "The software request could not be fully saved. "
                "Check the tickets, software_requests, and audit collections."
            ),
        ) from error


@app.get("/api/software/requests")
def get_software_requests():
    """List recent software provisioning requests."""
    try:
        documents = software_requests_collection.find().sort(
            "created_at", DESCENDING
        ).limit(100)
        requests = []
        for document in documents:
            document["_id"] = str(document["_id"])
            requests.append(document)
        return {"count": len(requests), "requests": requests}
    except PyMongoError as error:
        raise HTTPException(
            status_code=503,
            detail="Unable to retrieve software requests.",
        ) from error


# ============================================================

# 16. KNOWLEDGE RETRIEVAL HELPERS

# ============================================================



def get_full_knowledge_article(metadata, fallback_chunk=""):

    document_id = metadata.get("document_id")



    if document_id:

        article = knowledge_mongo_collection.find_one({

            "document_id": document_id

        })



        if article:

            return {

                "title": article.get(

                    "title",

                    metadata.get("title", "Knowledge article"),

                ),

                "category": article.get(

                    "category",

                    metadata.get("category", "General"),

                ),

                "content": article.get("content", ""),

            }



    title = metadata.get("title", "Knowledge article")

    content = fallback_chunk.strip()

    title_prefix = f"Title: {title}"



    if content.lower().startswith(title_prefix.lower()):

        content = content[len(title_prefix):].strip()



    return {

        "title": title,

        "category": metadata.get("category", "General"),

        "content": content,

    }





def clean_article_content(content):

    content = content.strip()



    if content.lower().startswith("problem:"):

        content = content[len("problem:"):].strip()



    return content





# ============================================================

# 17. PRESERVE SAFETY WARNINGS IN GENERATED ANSWERS

# ============================================================



SAFETY_WARNING_MARKERS = (

    "do not ",

    "never ",

    "must not ",

    "without authorisation",

    "without authorization",

    "not permitted",

    "prohibited",

)





def extract_safety_warnings(article_content: str) -> list[str]:

    sentences = re.split(

        r"(?<=[.!?])\s+",

        article_content.strip(),

    )



    warnings = []



    for sentence in sentences:

        normalised = f" {sentence.lower()} "



        if any(

            marker in normalised

            for marker in SAFETY_WARNING_MARKERS

        ):

            warnings.append(sentence.strip())



    return warnings





def append_missing_safety_warnings(answer, article_content):

    warnings = extract_safety_warnings(article_content)



    missing_warnings = [

        warning

        for warning in warnings

        if warning.casefold() not in answer.casefold()

    ]



    if missing_warnings:

        answer += "\n\n**Important safety instructions:**\n"

        answer += "\n".join(

            f"- {warning}" for warning in missing_warnings

        )



    return answer





def search_knowledge_chunks(question, result_limit=4):

    question_embedding = embedding_model.encode(

        question,

        normalize_embeddings=True,

    ).tolist()



    chunk_count = knowledge_collection.count()



    if chunk_count == 0:

        return []



    results = knowledge_collection.query(

        query_embeddings=[question_embedding],

        n_results=min(result_limit, chunk_count),

        include=["documents", "metadatas", "distances"],

    )



    documents = results["documents"][0] or []

    metadatas = results["metadatas"][0] or []

    distances = results["distances"][0] or []



    return [

        {

            "chunk": documents[index],

            "metadata": metadatas[index] or {},

            "distance": float(distances[index]),

        }

        for index in range(len(documents))

    ]





# ============================================================

# 18. SEARCH THE KNOWLEDGE BASE

# ============================================================


@app.get("/api/knowledge/articles")
def get_knowledge_articles():
    """Return all knowledge articles for the Knowledge Base page."""
    try:
        documents = knowledge_mongo_collection.find().sort(
            "document_id", 1
        )

        articles = []

        for document in documents:
            document["_id"] = str(document["_id"])
            articles.append(document)

        return {
            "count": len(articles),
            "articles": articles,
        }

    except PyMongoError as error:
        print(f"Knowledge catalogue error: {error}")
        raise HTTPException(
            status_code=503,
            detail="Unable to retrieve knowledge articles.",
        ) from error


@app.post("/api/knowledge/search")

def search_knowledge(request: KnowledgeSearchRequest):

    question = request.question.strip()



    if not question:

        raise HTTPException(

            status_code=422,

            detail="Question is required.",

        )



    try:

        matches = search_knowledge_chunks(question)

        articles_by_id = {}



        for match in matches:

            article = get_full_knowledge_article(

                match["metadata"],

                match["chunk"],

            )



            article_key = (

                match["metadata"].get("document_id")

                or article["title"]

            )



            if article_key in articles_by_id:

                continue



            articles_by_id[article_key] = {

                "title": article["title"],

                "category": article["category"],

                "content": article["content"],

                "distance": round(match["distance"], 4),

            }



        return {

            "question": question,

            "matches": list(articles_by_id.values()),

            "source": "ChromaDB chunk retrieval + MongoDB Atlas",

        }



    except Exception as error:

        print(f"Knowledge search error: {error}")



        raise HTTPException(

            status_code=500,

            detail="Knowledge search failed.",

        ) from error





# ============================================================

# 19. GENERATE A GROUNDED ANSWER WITH SMOLLM2

# ============================================================



def generate_grounded_answer(question, article_content):

    if llm_model is None or llm_tokenizer is None:

        raise RuntimeError("The language model is not loaded.")



    messages = [

        {

            "role": "system",

            "content": (

                "You are HelpPilot AI, an IT support assistant. "

                "Answer only using the supplied knowledge article. "

                "Do not invent troubleshooting steps, policies, "

                "or technical facts. Preserve important warnings. "

                "If the article does not answer the question, say "

                "that the user should contact IT Support. "

                "Give a concise, clear answer."

            ),

        },

        {

            "role": "user",

            "content": (

                f"Knowledge article:\n{article_content}\n\n"

                f"Employee question:\n{question}\n\n"

                "Answer using the knowledge article:"

            ),

        },

    ]



    prompt = llm_tokenizer.apply_chat_template(

        messages,

        tokenize=False,

        add_generation_prompt=True,

    )



    inputs = llm_tokenizer(

        prompt,

        return_tensors="pt",

        truncation=True,

        max_length=1024,

    )



    with llm_lock:

        with torch.inference_mode():

            output_tokens = llm_model.generate(

                **inputs,

                max_new_tokens=160,

                do_sample=False,

                pad_token_id=llm_tokenizer.eos_token_id,

                eos_token_id=llm_tokenizer.eos_token_id,

            )



    new_tokens = output_tokens[

        0, inputs["input_ids"].shape[1]:

    ]



    answer = llm_tokenizer.decode(

        new_tokens,

        skip_special_tokens=True,

    ).strip()



    if not answer:

        raise RuntimeError(

            "The language model returned an empty answer."

        )



    return answer





# ============================================================

# 20. ANSWER QUESTIONS USING RAG

# ============================================================



@app.post("/api/knowledge/answer")

def answer_knowledge_question(request: KnowledgeSearchRequest):

    question = request.question.strip()



    if not question:

        raise HTTPException(

            status_code=422,

            detail="Question is required.",

        )



    try:

        matches = search_knowledge_chunks(

            question,

            result_limit=4,

        )



        if not matches:

            return {

                "question": question,

                "answer": (

                    "I couldn't find supporting information "

                    "in the knowledge base. Please contact IT Support."

                ),

                "sources": [],

                "escalated": True,

                "reason": "no_search_results",

            }



        best_match = matches[0]

        best_distance = best_match["distance"]



        if best_distance > RETRIEVAL_DISTANCE_THRESHOLD:

            return {

                "question": question,

                "answer": (

                    "I couldn't find sufficiently relevant "

                    "information in the knowledge base. "

                    "Please contact IT Support."

                ),

                "sources": [],

                "escalated": True,

                "reason": "low_retrieval_relevance",

                "retrieval_distance": round(best_distance, 4),

            }



        article = get_full_knowledge_article(

            best_match["metadata"],

            best_match["chunk"],

        )



        source_title = article["title"]

        source_category = article["category"]

        article_content = clean_article_content(

            article["content"]

        )



        if not article_content:

            return {

                "question": question,

                "answer": (

                    "The matching knowledge article has no usable "

                    "content. Please contact IT Support."

                ),

                "sources": [],

                "escalated": True,

                "reason": "empty_article_content",

            }



        try:

            answer = generate_grounded_answer(

                question,

                article_content,

            )



            answer = append_missing_safety_warnings(

                answer,

                article_content,

            )



        except Exception as llm_error:

            print(f"LLM generation error: {llm_error}")



            return {

                "question": question,

                "answer": article_content,

                "sources": [{

                    "title": source_title,

                    "category": source_category,

                    "distance": round(best_distance, 4),

                }],

                "escalated": False,

                "answer_mode": "retrieved_knowledge_fallback",

                "message": (

                    "LLM generation failed. The original "

                    "knowledge article is shown without rewriting."

                ),

            }



        return {

            "question": question,

            "answer": answer,

            "sources": [{

                "title": source_title,

                "category": source_category,

                "distance": round(best_distance, 4),

            }],

            "escalated": False,

            "answer_mode": "rag_llm",

            "message": (

                "Answer generated using SmolLM2 with retrieved "

                "knowledge from the cited article."

            ),

        }



    except Exception as error:

        print(f"Knowledge answer error: {error}")



        raise HTTPException(

            status_code=500,

            detail="Unable to retrieve an answer right now.",

        ) from error





# ============================================================

# 21. VIEW THE AUDIT LOG

# ============================================================



@app.get("/api/audit")

def get_audit_logs():

    try:

        documents = audit_collection.find().sort(

            "created_at",

            DESCENDING,

        ).limit(100)



        logs = []



        for document in documents:

            document["_id"] = str(document["_id"])

            logs.append(document)



        return {

            "count": len(logs),

            "audit_logs": logs,

        }



    except PyMongoError as error:

        raise HTTPException(

            status_code=503,

            detail="Unable to retrieve audit logs.",

        ) from error
