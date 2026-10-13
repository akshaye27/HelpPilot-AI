import os
from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING, DESCENDING

# Load the database settings from .env
load_dotenv()

mongodb_uri = os.getenv("MONGODB_URI")
database_name = os.getenv("MONGODB_DATABASE", "helppilot")

# Connect to MongoDB Atlas
client = MongoClient(
    mongodb_uri,
    serverSelectionTimeoutMS=10000
)

try:
    # Verify the connection
    client.admin.command("ping")

    # Select our application database
    db = client[database_name]

    # Create the required collections if they do not exist
    required_collections = [
        "tickets",
        "knowledge",
        "chat",
        "audit"
    ]

    existing_collections = db.list_collection_names()

    for collection_name in required_collections:
        if collection_name not in existing_collections:
            db.create_collection(collection_name)
            print(f"Created collection: {collection_name}")
        else:
            print(f"Collection already exists: {collection_name}")

    # Add indexes to make common lookups faster
    db.tickets.create_index(
        [("ticket_id", ASCENDING)],
        unique=True,
        sparse=True
    )

    db.tickets.create_index(
        [("created_at", DESCENDING)]
    )

    db.knowledge.create_index(
        [("document_id", ASCENDING)],
        unique=True,
        sparse=True
    )

    print("\nSUCCESS: HelpPilot AI database initialized.")
    print(f"Database name: {database_name}")
    print("Required collections are ready.")

finally:
    client.close()
