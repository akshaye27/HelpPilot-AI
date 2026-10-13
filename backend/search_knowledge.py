import os

import chromadb
from sentence_transformers import SentenceTransformer

# Use the same persistent ChromaDB folder as the indexing script
chroma_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "chroma_db",
)

client = chromadb.PersistentClient(path=chroma_path)
collection = client.get_collection(name="helpdesk_knowledge")

# Load the same embedding model used to index the articles
print("Loading embedding model...")
model = SentenceTransformer(
    "sentence-transformers/all-MiniLM-L6-v2"
)

# Try questions that differ from the article wording
questions = [
    "I cannot connect to the company network when working remotely.",
    "I forgot my login password and my account is blocked.",
    "I need permission to get a new application installed.",
    "My emails are not appearing in Outlook.",
]

for question in questions:
    print("\n" + "=" * 70)
    print(f"QUESTION: {question}")

    # Convert the question into a vector
    query_embedding = model.encode(
        question,
        normalize_embeddings=True,
    ).tolist()

    # Retrieve the two most relevant articles
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=2,
        include=["documents", "metadatas", "distances"],
    )

    for index, metadata in enumerate(results["metadatas"][0]):
        print(f"\nResult {index + 1}: {metadata['title']}")
        print(f"Category: {metadata['category']}")
        print(
            "Distance:",
            round(results["distances"][0][index], 4),
        )
        print(results["documents"][0][index][:250] + "...")

print("\nSemantic search test completed.")
