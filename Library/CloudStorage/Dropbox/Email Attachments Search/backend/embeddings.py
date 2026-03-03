import json
import os
import numpy as np
import faiss
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

PDF_FOLDER = os.getenv("PDF_FOLDER")
INDEX_FILE = os.path.join(os.path.dirname(__file__), "index.json")
VECTOR_DB_FILE = os.path.join(os.path.dirname(__file__), "vector.faiss")
METADATA_FILE = os.path.join(os.path.dirname(__file__), "metadata.json")

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_embedding(text, model="text-embedding-3-small"):
    """Generate embeddings using OpenAI."""
    if not text or not text.strip():
        return None
    response = client.embeddings.create(
        input=text[:8191],  # API limit
        model=model
    )
    return response.data[0].embedding

def create_vector_db():
    """Create FAISS vector database from indexed PDFs."""
    # Load documents
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        documents = json.load(f)
    
    embeddings = []
    metadata = []
    
    for i, doc in enumerate(documents):
        text = doc.get("text", "")[:2000]  # Limit text for embedding
        if not text.strip():
            continue
        
        print(f"Embedding {i+1}/{len(documents)}: {doc['filename']}")
        embedding = get_embedding(text)
        if embedding:
            embeddings.append(embedding)
            metadata.append({
                "path": doc.get("relative_path", doc["path"]),  # Use relative path
                "filename": doc["filename"],
                "snippet": text[:300]
            })
    
    # Create FAISS index
    embeddings_array = np.array(embeddings).astype("float32")
    dimension = embeddings_array.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings_array)
    
    # Save index and metadata
    faiss.write_index(index, VECTOR_DB_FILE)
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    
    print(f"✅ Vector DB created with {len(metadata)} documents")

def search(query, top_k=5):
    """Search vector database using semantic similarity."""
    if not os.path.exists(VECTOR_DB_FILE):
        return []
    
    # Generate query embedding
    query_embedding = get_embedding(query)
    if not query_embedding:
        return []
    
    # Load FAISS index and metadata
    index = faiss.read_index(VECTOR_DB_FILE)
    with open(METADATA_FILE, "r", encoding="utf-8") as f:
        metadata = json.load(f)
    
    # Search
    query_vector = np.array([query_embedding]).astype("float32")
    distances, indices = index.search(query_vector, top_k)
    
    results = [metadata[i] for i in indices[0]]
    return results

if __name__ == "__main__":
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        exit(1)
    create_vector_db()
