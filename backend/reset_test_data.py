
import os
from dotenv import load_dotenv
from pymongo import MongoClient

# Load the existing backend/.env configuration
load_dotenv()

mongo_uri = os.getenv("MONGODB_URI")
database_name = os.getenv("MONGODB_DATABASE", "helppilot")

if not mongo_uri:
    raise ValueError("MONGODB_URI was not found in the backend .env file.")

client = MongoClient(mongo_uri, serverSelectionTimeoutMS=10000)
database = client[database_name]

# Collections to clear: test records only
collections_to_clear = [
    "tickets",
    "chat",
    "audit",
    "software_requests",
    "counters",
]

print(f"\nDatabase: {database_name}")
print("\nThe following collections will be cleared:")

for collection_name in collections_to_clear:
    count = database[collection_name].count_documents({})
    print(f"  {collection_name}: {count} document(s)")

print("\nThe knowledge collection and ChromaDB will NOT be deleted.")
confirmation = input(
    "\nType DELETE TEST DATA to continue: "
).strip()

if confirmation != "DELETE TEST DATA":
    print("Cancelled. No records were deleted.")
else:
    try:
        client.admin.command("ping")

        for collection_name in collections_to_clear:
            result = database[collection_name].delete_many({})
            print(
                f"Cleared {collection_name}: "
                f"{result.deleted_count} document(s) deleted."
            )

        print("\nReset complete. Your knowledge base is preserved.")

    finally:
        client.close()
