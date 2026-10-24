from rag import retrieve_documents


question = "What is Prisha Mehta's department?"
role = "hr"

results = retrieve_documents(question, role)

print("\nRETRIEVED CHUNKS:")

for number, (document, metadata) in enumerate(
    zip(
        results["documents"][0],
        results["metadatas"][0]
    ),
    start=1
):
    print(f"\n--- Chunk {number} ---")
    print("Source:", metadata["source"])
    print("Department:", metadata["department"])
    print(document)