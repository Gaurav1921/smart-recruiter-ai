import os
import glob
from docling.document_converter import DocumentConverter
from opensearchpy import OpenSearch
from google import genai
from dotenv import load_dotenv

# 1. Load Environment Variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENSEARCH_HOST = os.getenv("OPENSEARCH_HOST", "localhost")
OPENSEARCH_PORT = int(os.getenv("OPENSEARCH_PORT", 9200))

# 2. Setup Clients
print("🔌 Connecting to Gemini...")
client = genai.Client(api_key=GEMINI_API_KEY)

print(f"🔌 Connecting to OpenSearch at {OPENSEARCH_HOST}:{OPENSEARCH_PORT}...")
os_client = OpenSearch(
    hosts=[{'host': OPENSEARCH_HOST, 'port': OPENSEARCH_PORT}],
    http_compress=True,
    use_ssl=False,
    verify_certs=False,
    ssl_assert_hostname=False,
    ssl_show_warn=False
)

INDEX_NAME = "resume-index-v2"

# 3. Create Index
def create_index():
    index_body = {
        "settings": {"index.knn": True},
        "mappings": {
            "properties": {
                "embedding": {
                    "type": "knn_vector",
                    "dimension": 768,
                    "method": {"name": "hnsw", "engine": "lucene"}
                },
                "text": {"type": "text"},          # The Chunk Text (for search)
                "full_text": {"type": "text"},     # The Whole Resume (for grading)
                "filename": {"type": "keyword"},
                "chunk_id": {"type": "keyword"}
            }
        }
    }
    
    if not os_client.indices.exists(index=INDEX_NAME):
        os_client.indices.create(index=INDEX_NAME, body=index_body)
        print(f"✅ Created new index: {INDEX_NAME}")
    else:
        # Optional: Delete old index to enforce new mapping if needed
        # os_client.indices.delete(index=INDEX_NAME) 
        print(f"ℹ️  Index {INDEX_NAME} already exists.")

# 4. Helper: Semantic Chunking Logic
def chunk_markdown_by_headers(markdown_text):
    """
    Splits a markdown document into semantic chunks based on headers (##).
    """
    chunks = []
    current_chunk = []
    
    lines = markdown_text.split('\n')
    
    for line in lines:
        # Detect Header lines (Docling usually outputs ## for sections)
        if line.strip().startswith('##') or line.strip().startswith('# '):
            if current_chunk:
                # Save previous chunk
                chunks.append('\n'.join(current_chunk))
            # Start new chunk with this header
            current_chunk = [line]
        else:
            current_chunk.append(line)
            
    # Append the last chunk
    if current_chunk:
        chunks.append('\n'.join(current_chunk))
        
    return chunks

# 5. Helper to get Embeddings
def get_embedding(text):
    try:
        # Embed only the chunk (efficient)
        result = client.models.embed_content(
            model="models/text-embedding-004",
            contents=text[:8000] 
        )
        return result.embeddings[0].values
    except Exception as e:
        print(f"⚠️ Embedding Error: {e}")
        return None

# 6. Main Processing Loop
def ingest_data():
    converter = DocumentConverter()
    files = glob.glob("data/**/*.pdf", recursive=True)
    
    print(f"🚀 Found {len(files)} PDFs. Starting Semantic Ingestion...")
    
    count = 0
    for pdf_path in files: # Removing limit to process all
        try:
            filename = os.path.basename(pdf_path)
            print(f"📄 Processing: {filename}...")

            # A. Parse PDF
            doc_result = converter.convert(pdf_path)
            full_markdown = doc_result.document.export_to_markdown()
            
            # B. Split into Semantic Chunks
            chunks = chunk_markdown_by_headers(full_markdown)
            print(f"   -> Split into {len(chunks)} semantic chunks.")

            # C. Process Each Chunk
            for i, chunk_text in enumerate(chunks):
                if len(chunk_text.strip()) < 50: continue # Skip empty/tiny chunks
                
                vector = get_embedding(chunk_text)
                
                if vector:
                    # D. Index Chunk
                    # Crucial: We store 'chunk_text' for search, but 'full_text' for context
                    doc_body = {
                        "text": chunk_text,          # Search hits this
                        "full_text": full_markdown,  # Analysis uses this
                        "embedding": vector,
                        "filename": filename,
                        "chunk_id": f"{filename}_{i}"
                    }
                    
                    # Unique ID for every chunk
                    os_client.index(
                        index=INDEX_NAME, 
                        body=doc_body, 
                        id=f"{filename}_{i}"
                    )
            
            count += 1
            print(f"   ✅ Indexed {filename}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")

    print(f"\n🎉 Done! Successfully processed {count} documents.")

if __name__ == "__main__":
    create_index()
    ingest_data()