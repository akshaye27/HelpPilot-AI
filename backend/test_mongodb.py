
import os
from dotenv import load_dotenv
from pymongo import MongoClient

# Load settings from the backend/.env file
load_dotenv()

# Read the MongoDB connection string securely
mongodb_uri = os.getenv("MONGODB_URI")
database_name = os.getenv("MONGODB_DATABASE", "helppilot")

if not mongodb_uri:
    raise ValueError(
        "MONGODB_URI was not found. Check your backend/.env file."
    )

client = None

try:
    # Connect to Atlas and limit how long we wait for a response
    client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=10000)

    # Ask MongoDB to confirm that the connection works
    client.admin.command("ping")

    print("SUCCESS: Connected to MongoDB Atlas!")
    print(f"Database configured: {database_name}")

except Exception as error:
    print("CONNECTION FAILED.")
    print(f"Error type: {type(error).__name__}")
    print(f"Details: {error}")

finally:
    if client is not None:
        client.close()
