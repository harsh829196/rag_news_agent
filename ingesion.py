import sqlite3
import numpy as np
from sentence_transformers import SentenceTransformer
from database.chromadb import collection
from embedding import EmbeddingManager
from processing.chunker import splitter

conn = sqlite3.connect("news.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    url TEXT UNIQUE,
    source TEXT,
    published TEXT,
    content TEXT,
    embedded INTEGER DEFAULT 0
)
""")
conn.commit()

encoding = SentenceTransformer('all-MiniLM-L6-v2')
import json
import feedparser #it is a library that parses RSS feeds and returns a Python object that can be easily manipulated.
with open("feeds.json") as f:
    feeds = json.load(f)["feeds"]


for url in feeds:
    feed = feedparser.parse(url)

    for article in feed.entries:
        print(article.title)
        print(article.link)
        print(article.published)
        print("-" * 40)


import time

from newspaper import Article


# =========================================================
# INITIALIZE ONCE
# =========================================================

# chroma_client = chromadb.PersistentClient(
#     path="./chroma_db"
# )

# collection = chroma_client.get_or_create_collection(
#     name="my_collection_new1"
# )

embedding_manager = EmbeddingManager()

EMBED_BATCH_LIMIT = 20  # process at most this many articles per cycle, avoids long first-run blocking


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def get_unembedded_articles(cursor, limit=EMBED_BATCH_LIMIT):
    cursor.execute("""
        SELECT id, content, source, title
        FROM articles
        WHERE embedded = 0
        AND content IS NOT NULL
        LIMIT ?
    """, (limit,))
    return cursor.fetchall()


def mark_embedded(conn, article_id):
    conn.execute(
        "UPDATE articles SET embedded = 1 WHERE id = ?",
        (article_id,)
    )
    conn.commit()


# =========================================================
# MAIN PIPELINE
# =========================================================

def after_10minutes():

    total_start = time.time()

    print("\n" + "=" * 50)
    print("STARTING NEWS INGESTION")
    print("=" * 50)


    # -----------------------------------------------------
    # 1. RSS INGESTION
    # -----------------------------------------------------

    rss_start = time.time()

    print("\n[1] Fetching RSS feeds...")

    new_articles = 0

    for feed_url in feeds:

        try:
            feed = feedparser.parse(feed_url)
            source_name = feed.feed.get("title", feed_url)  # FIX: capture outlet name from the feed

            for article in feed.entries:

                title = article.get("title", "")
                url = article.get("link", "")
                published = article.get("published", "")

                if not url:
                    continue

                cursor.execute("""
                    INSERT OR IGNORE INTO articles
                    (title, url, source, published)
                    VALUES (?, ?, ?, ?)
                """, (
                    title,
                    url,
                    source_name,   # FIX: source now actually stored
                    published
                ))

                if cursor.rowcount > 0:
                    new_articles += 1

        except Exception as e:
            print(f"RSS feed failed: {feed_url}")
            print(f"Error: {e}")

    conn.commit()

    print(f"New articles found: {new_articles}")
    print(
        f"RSS time: {time.time() - rss_start:.2f} seconds"
    )


    # -----------------------------------------------------
    # 2. DOWNLOAD ARTICLE CONTENT
    # -----------------------------------------------------

    download_start = time.time()

    print("\n[2] Downloading article content...")

    cursor.execute("""
        SELECT id, url
        FROM articles
        WHERE content IS NULL
        LIMIT ?
    """, (EMBED_BATCH_LIMIT * 2,))  # cap this stage too, so downloads don't run away on first launch

    articles_to_download = cursor.fetchall()

    print(
        f"Articles to download: "
        f"{len(articles_to_download)}"
    )

    downloaded = 0

    for article_id, url in articles_to_download:

        try:

            art = Article(url)

            art.download()
            art.parse()

            content = art.text

            if not content:
                print(
                    f"No content: article {article_id}"
                )
                continue

            cursor.execute("""
                UPDATE articles
                SET content = ?
                WHERE id = ?
            """, (
                content,
                article_id
            ))

            downloaded += 1

        except Exception as e:

            print(
                f"Failed article {article_id}: {e}"
            )

    conn.commit()

    print(f"Successfully downloaded: {downloaded}")

    print(
        f"Download time: "
        f"{time.time() - download_start:.2f} seconds"
    )


    # -----------------------------------------------------
    # 3. GET UNEMBEDDED ARTICLES
    # -----------------------------------------------------

    embedding_start = time.time()

    print("\n[3] Finding articles to embed...")

    articles = get_unembedded_articles(cursor)

    print(
        f"Articles waiting for embeddings (this cycle, capped at {EMBED_BATCH_LIMIT}): "
        f"{len(articles)}"
    )


    # -----------------------------------------------------
    # 4. CHUNK + EMBED + STORE
    # -----------------------------------------------------

    total_chunks = 0
    embedded_articles = 0

    for article_id, content, source, title in articles:

        try:

            # DIAGNOSTIC: catch abnormally large content (bad scrape) before chunking
            print(
                f"Article {article_id}: content length = {len(content)} chars"
            )
            if len(content) > 20000:
                print(
                    f"  WARNING: unusually long content, likely a bad scrape — skipping"
                )
                mark_embedded(conn, article_id)  # mark done so it doesn't retry forever
                continue

            # Chunk
            chunks = splitter(content)

            if not chunks:
                print(
                    f"No chunks: article {article_id}"
                )
                continue

            print(
                f"Article {article_id}: "
                f"{len(chunks)} chunks"
            )

            total_chunks += len(chunks)


            # Embeddings (progress bar off — adds overhead in a loop)
            embeddings = (
                embedding_manager.Get_embadding(chunks)
            )
            if hasattr(embeddings, "tolist"):
                embeddings = embeddings.tolist()


            # IDs
            ids = [
                f"{article_id}_{i}"
                for i in range(len(chunks))
            ]


            # Metadata
            metadatas = [
                {
                    "article_id": int(article_id),
                    "source": str(source or ""),
                    "title": str(title or "")
                }
                for _ in chunks
            ]


            # Store in ChromaDB
            collection.add(
                embeddings=embeddings,
                documents=chunks,
                metadatas=metadatas,
                ids=ids
            )


            # Only mark after successful Chroma insertion
            mark_embedded(
                conn,
                article_id
            )

            embedded_articles += 1

        except Exception as e:

            print(
                f"Embedding failed for article "
                f"{article_id}: {e}"
            )


    # -----------------------------------------------------
    # 5. SUMMARY
    # -----------------------------------------------------

    embedding_time = time.time() - embedding_start
    total_time = time.time() - total_start

    print("\n" + "=" * 50)
    print("INGESTION COMPLETE")
    print("=" * 50)

    print(
        f"Articles embedded: {embedded_articles}"
    )

    print(
        f"Total chunks: {total_chunks}"
    )

    print(
        f"Embedding time: {embedding_time:.2f} seconds"
    )

    print(
        f"TOTAL TIME: {total_time:.2f} seconds"
    )

    print("=" * 50)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ingest news articles and embeddings")
    parser.add_argument(
        "--watch",
        action="store_true",
        help="run ingestion every 10 minutes until interrupted",
    )
    args = parser.parse_args()

    after_10minutes()

    if args.watch:
        import schedule

        schedule.every(10).minutes.do(after_10minutes)
        print("Watching for new articles every 10 minutes. Press Ctrl+C to stop.")
        try:
            while True:
                schedule.run_pending()
                time.sleep(30)
        except KeyboardInterrupt:
            print("\nIngestion stopped.")

