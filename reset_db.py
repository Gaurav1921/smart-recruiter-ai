from opensearchpy import OpenSearch
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenSearch(
    hosts=[{'host': os.getenv("OPENSEARCH_HOST", "localhost"), 'port': int(os.getenv("OPENSEARCH_PORT", 9200))}],
    http_compress=True,
    use_ssl=False,
    verify_certs=False,
    ssl_assert_hostname=False,
    ssl_show_warn=False
)

index_name = "resume-index-v2"

if client.indices.exists(index=index_name):
    client.indices.delete(index=index_name)
    print(f"🗑️ SUCCESS: Deleted index '{index_name}'. You can now re-ingest.")
else:
    print(f"Index '{index_name}' does not exist. You are good to go.")