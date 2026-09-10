from graph import app

def main():
    query = input("Ask something: ")
    result = app.invoke({
        "query": query,
        "messages": [],
        "retrieved_docs": []
    })
    print(result["answer"])

if __name__ == "__main__":
    main()