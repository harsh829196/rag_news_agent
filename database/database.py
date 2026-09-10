import sqlite3

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

cursor.execute("""
SELECT id, url
FROM articles
WHERE content IS NULL
""")
articles= cursor.fetchall() 

from newspaper import Article

for article_id, url in articles:

    art = Article(url)
    art.download()
    art.parse()

    content = art.text

    cursor.execute("""
    UPDATE articles
    SET content = ?
    WHERE id = ?
    """, (content, article_id))

conn.commit()



