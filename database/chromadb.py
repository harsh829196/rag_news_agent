import time
import chromadb
from newspaper import Article


# =========================================================
# INITIALIZE ONCE
# =========================================================

chroma_client = chromadb.PersistentClient(
    path="./chroma_db"
)

collection = chroma_client.get_or_create_collection(
    name="my_collection_new1"
)
