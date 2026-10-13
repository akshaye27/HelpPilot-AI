
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from sentence_transformers import SentenceTransformer
import chromadb


# --------------------------------------------------
# 1. Load MongoDB settings from the .env file
# --------------------------------------------------

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
DATABASE_NAME = os.getenv("MONGODB_DATABASE", "helppilot")

if not MONGODB_URI:
    raise ValueError(
        "MONGODB_URI is missing. Check your backend/.env file."
    )


# --------------------------------------------------
# 2. Connect to MongoDB Atlas and ChromaDB
# --------------------------------------------------

mongo_client = MongoClient(MONGODB_URI)
database = mongo_client[DATABASE_NAME]
knowledge_collection = database["knowledge"]

chroma_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "chroma_db"
)

chroma_client = chromadb.PersistentClient(path=chroma_path)

vector_collection = chroma_client.get_or_create_collection(
    name="helpdesk_knowledge",
    metadata={"hnsw:space": "cosine"}
)


# --------------------------------------------------
# 3. Load the embedding model
# --------------------------------------------------

print("Loading the embedding model...")

embedding_model = SentenceTransformer(
    "sentence-transformers/all-MiniLM-L6-v2"
)


# --------------------------------------------------
# 4. Split an article into smaller chunks
# --------------------------------------------------

def split_into_chunks(text, chunk_size=45, overlap=8):
    """
    Split text into chunks of words.

    chunk_size = maximum number of words per chunk.
    overlap = words shared between consecutive chunks.
    """

    words = text.split()

    if not words:
        return []

    chunks = []
    start = 0

    while start < len(words):
        end = start + chunk_size
        chunk_words = words[start:end]

        chunks.append(" ".join(chunk_words))

        if end >= len(words):
            break

        # Reuse a few words to preserve context.
        start = end - overlap

    return chunks


# --------------------------------------------------
# 5. Read articles from MongoDB
# --------------------------------------------------

print("Connecting to MongoDB Atlas...")

mongo_client.admin.command("ping")

articles = list(
    knowledge_collection.find({}).sort("document_id", 1)
)

if not articles:
    raise ValueError(
        "No knowledge articles found in MongoDB's knowledge collection."
    )

print(f"Found {len(articles)} knowledge articles.")


# --------------------------------------------------
# 6. Create chunks and preserve their source details
# --------------------------------------------------

chunk_ids = []
chunk_texts = []
chunk_metadatas = []

for article in articles:
    document_id = str(
        article.get("document_id")
        or article.get("_id")
    )

    title = article.get("title", "Untitled article")
    category = article.get("category", "General")
    content = article.get("content", "")

    if not content.strip():
        print(f"Skipping article with no content: {title}")
        continue

    article_chunks = split_into_chunks(content)

    for chunk_index, chunk in enumerate(article_chunks):
        # Repeat the title so every chunk retains its context.
        searchable_text = f"Title: {title}\n\n{chunk}"

        chunk_id = f"{document_id}_chunk_{chunk_index}"

        chunk_ids.append(chunk_id)
        chunk_texts.append(searchable_text)

        chunk_metadatas.append({
            "document_id": document_id,
            "title": str(title),
            "category": str(category),
            "chunk_index": chunk_index,
            "total_chunks": len(article_chunks)
        })

if not chunk_texts:
    raise ValueError("No usable text chunks were created.")

print(f"Created {len(chunk_texts)} chunks.")


# --------------------------------------------------
# 7. Generate embeddings for the chunks
# --------------------------------------------------

print("Generating embeddings...")

embeddings = embedding_model.encode(
    chunk_texts,
    normalize_embeddings=True,
    show_progress_bar=True
)

embedding_vectors = embeddings.tolist()


# --------------------------------------------------
# 8. Replace the old article-level index
# --------------------------------------------------

print("Removing the old ChromaDB index...")

existing_data = vector_collection.get()
existing_ids = existing_data.get("ids", [])

if existing_ids:
    vector_collection.delete(ids=existing_ids)

print("Indexing the new chunks...")

vector_collection.upsert(
    ids=chunk_ids,
    documents=chunk_texts,
    metadatas=chunk_metadatas,
    embeddings=embedding_vectors
)


# --------------------------------------------------
# 9. Verify the new index
# --------------------------------------------------

print("\nChunk indexing completed successfully!")
print(f"Knowledge articles: {len(articles)}")
print(f"Chunks indexed: {len(chunk_ids)}")
print(f"ChromaDB collection: {vector_collection.name}")
print(f"Stored vectors: {vector_collection.count()}")

print("\nSample chunks:")

for index, text in enumerate(chunk_texts[:3], start=1):
    print(f"\n--- Chunk {index} ---")
    print(text[:250])

mongo_client.close()
