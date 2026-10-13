import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING

load_dotenv()

mongodb_uri = os.getenv("MONGODB_URI")
database_name = os.getenv("MONGODB_DATABASE", "helppilot")

if not mongodb_uri:
    raise ValueError("MONGODB_URI is missing from .env")

client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=10000)
db = client[database_name]
knowledge_collection = db["knowledge"]

# Six sample IT support knowledge articles.
# These are prototype articles, not official company policies.
articles = [
    {
        "document_id": "KB001",
        "title": "VPN Connectivity Troubleshooting",
        "category": "Network",
        "content": (
            "Problem: The corporate VPN will not connect. "
            "Check whether the device has internet access. "
            "Confirm that the user is entering the correct "
            "corporate username and that multi-factor authentication "
            "is completed. Restart the approved VPN client and "
            "retry the connection. Record any error message. "
            "If the issue continues, escalate to Network Support. "
            "Never ask users to share their passwords."
        ),
    },
    {
        "document_id": "KB002",
        "title": "Password Reset and Account Lockout",
        "category": "Access",
        "content": (
            "Problem: A user has forgotten a password or is locked "
            "out. Direct the user to the organisation's approved "
            "password reset portal. Verify identity using the "
            "approved process before any account recovery. If the "
            "account remains locked or the reset fails, escalate "
            "to IT Support. Never request or store the user's "
            "current password."
        ),
    },
    {
        "document_id": "KB003",
        "title": "Software Installation Request",
        "category": "Software",
        "content": (
            "Problem: A user needs a software application installed. "
            "Check the approved software catalogue and verify that "
            "the requested application is permitted. Submit a "
            "software provisioning request with the application "
            "name, business reason, device, and required approval. "
            "Do not bypass administrative controls or install "
            "unapproved software."
        ),
    },
    {
        "document_id": "KB004",
        "title": "Outlook Email Synchronisation",
        "category": "Application",
        "content": (
            "Problem: Outlook is not synchronising email. Check "
            "internet connectivity and whether Outlook is in "
            "offline mode. Restart Outlook and check the service "
            "status if available. Record any error message and "
            "the approximate time the issue began. Do not delete "
            "mail profiles or data files without authorisation. "
            "Escalate persistent problems to IT Support."
        ),
    },
    {
        "document_id": "KB005",
        "title": "Slow Computer and Performance Issues",
        "category": "Device",
        "content": (
            "Problem: A computer is running slowly. Save open work, "
            "check available disk space, close unnecessary "
            "applications, and restart the device if practical. "
            "Record when the slowdown occurs and whether a specific "
            "application is affected. Do not disable security "
            "software. Escalate recurring performance problems "
            "to the desktop support team."
        ),
    },
    {
        "document_id": "KB006",
        "title": "Multi-Factor Authentication Problems",
        "category": "Access",
        "content": (
            "Problem: A user cannot complete multi-factor "
            "authentication. Check that the device has network "
            "connectivity and that the device time is correct. "
            "Ask the user to follow the approved recovery process "
            "if their registered authentication device is "
            "unavailable. Verify identity before changing "
            "authentication settings. Escalate suspected account "
            "compromise immediately through the approved security "
            "process. Never ask for authentication codes."
        ),
    },
]

try:
    client.admin.command("ping")

    # Ensure document IDs are unique.
    knowledge_collection.create_index(
        [("document_id", ASCENDING)],
        unique=True,
        sparse=True
    )

    inserted = 0
    updated = 0

    for article in articles:
        article["updated_at"] = datetime.now(
            timezone.utc
        ).isoformat()

        result = knowledge_collection.update_one(
            {"document_id": article["document_id"]},
            {"$set": article},
            upsert=True,
        )

        if result.upserted_id is not None:
            inserted += 1
        else:
            updated += 1

    print("Knowledge base setup successful.")
    print(f"New articles added: {inserted}")
    print(f"Existing articles updated: {updated}")
    print(
        "Total knowledge articles:",
        knowledge_collection.count_documents({})
    )

finally:
    client.close()
