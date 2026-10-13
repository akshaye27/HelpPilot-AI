
import os

import chromadb
from dotenv import load_dotenv
from pymongo import MongoClient
from sentence_transformers import SentenceTransformer

# 1. Load MongoDB settings
load_dotenv()

mongodb_uri = os.getenv("MONGODB_URI")
database_name = os.getenv("MONGODB_DATABASE", "helppilot")

if not mongodb_uri:
    raise ValueError("MONGODB_URI is missing from backend/.env")

# 2. Connect to MongoDB Atlas
mongo_client = MongoClient(
    mongodb_uri,
    serverSelectionTimeoutMS=10000
)

try:
    mongo_client.admin.command("ping")
    db = mongo_client[database_name]

    # 3. Read the knowledge articles from MongoDB
    articles = list(
        db["knowledge"].find(
            {},
            {
                "_id": 0,
                "document_id": 1,
                "title": 1,
                "category": 1,
                "content": 1,
            },
        )
    )

    if not articles:
        raise RuntimeError(
            "No knowledge articles found. Run seed_knowledge.py first."
        )

    # 4. Load the local persistent ChromaDB vector store
    chroma_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "chroma_db",
    )

    chroma_client = chromadb.PersistentClient(path=chroma_path)

    collection = chroma_client.get_or_create_collection(
        name="helpdesk_knowledge",
        metadata={"description": "HelpPilot IT support knowledge articles"},
    )

    # 5. Load the open-source Hugging Face embedding model
    print("Loading embedding model; first download may take a few minutes...")

    model = SentenceTransformer(
        "sentence-transformers/all-MiniLM-L6-v2"
    )

    # 6. Prepare article text and metadata
    ids = []
    documents = []
    metadatas = []

    for article in articles:
        document_id = article.get("document_id")
        title = article.get("title")
        content = article.get("content")
        category = article.get("category", "General")

        if not all([document_id, title, content]):
            print(f"Skipping incomplete article: {document_id}")
            continue

        ids.append(document_id)
        documents.append(f"Title: {title}\n\n{content}")
        metadatas.append({
            "title": title,
            "category": category,
        })

    if not ids:
        raise RuntimeError("No valid knowledge articles to index.")

    # 7. Convert article text into numerical vectors
    embeddings = model.encode(
        documents,
        normalize_embeddings=True,
        show_progress_bar=True,
    ).tolist()

    # 8. Save or update the vectors in ChromaDB
    collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
        embeddings=embeddings,
    )

    print("\nSUCCESS: Knowledge articles indexed.")
    print(f"Articles read from MongoDB: {len(articles)}")
    print(f"Articles indexed: {len(ids)}")
    print(f"ChromaDB collection: {collection.name}")
    print(f"Stored vector count: {collection.count()}")
    print(f"Vector database location: {chroma_path}")

finally:
    mongo_client.close()
