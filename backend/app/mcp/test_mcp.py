"""
Minimal local test (no MCP client needed):
- Calls the tool function directly
- Prints chunk + citation consistency
"""

from app.mcp.tools import recipe_rag_query


def main():
    res = recipe_rag_query(
        query="What are cheap protein options mentioned in the cookbook?",
        constraints={"top_k": 5},
    )

    print("latency_ms:", res.latency_ms)
    print("chunks:", len(res.chunks))
    print("citations:", len(res.citations))

    # Rule: citations must match chunks
    assert len(res.chunks) == len(res.citations), "chunks/citations length mismatch"

    for i, (ch, cit) in enumerate(zip(res.chunks, res.citations), start=1):
        assert ch.chunk_id == cit.chunk_id, "chunk_id mismatch"
        assert ch.source == cit.source, "source mismatch"
        assert ch.page == cit.page, "page mismatch"
        print(f"\n--- Evidence #{i} ---")
        print("source:", ch.source)
        print("page:", ch.page)
        print("chunk_id:", ch.chunk_id)
        print("text preview:", ch.text[:200].replace("\n", " ") + ("..." if len(ch.text) > 200 else ""))

    print("\nOK: tool output is consistent and grounded.")


if __name__ == "__main__":
    main()
