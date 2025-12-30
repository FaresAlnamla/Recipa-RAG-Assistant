from app.rag.retrieval import retrieve_docs

def test_metadata():
    docs = retrieve_docs("test", k=1)
    print("METADATA:", docs[0].metadata)
    print("CONTENT:", docs[0].page_content[:150])

if __name__ == "__main__":
    test_metadata()
