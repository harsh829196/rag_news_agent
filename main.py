from graph import app

def main():
    print("News agent ready. Type 'exit' or 'quit' to stop.")

    while True:
        try:
            query = input("\nAsk something: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if query.lower() in {"exit", "quit"}:
            print("Goodbye!")
            break
        if not query:
            continue

        try:
            result = app.invoke({
                "query": query,
                "messages": [],
                "retrieved_docs": []
            })
            print(result["answer"])
        except Exception as error:
            print(f"Unable to answer that question: {error}")

if __name__ == "__main__":
    main()