## chunking the text into smaller pieces for better processing and embedding

from langchain_text_splitters import RecursiveCharacterTextSplitter

def splitter(text, chunk_size=1000, chunk_overlap=200):
    split = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", " ", ""]
    )

    chunks = split.split_text(text)

    ##print(f"Created {len(chunks)} chunks")

    return chunks