import csv
from pathlib import Path

import chromadb
#Divides large markdown files into smaller chunks and splits at sensible places
from langchain_text_splitters import RecursiveCharacterTextSplitter


CHROMA_PATH = "chroma_db"
#Collection holds document text, embedding, ID, metadata
COLLECTION_NAME = "company_documents"

DATA_FOLDER = Path("data")
HR_CSV_PATH = DATA_FOLDER / "hr" / "hr_data.csv"


# Connect to ChromaDB.
client = chromadb.PersistentClient(path=CHROMA_PATH)


# Rebuild the collection whenever ingest.py runs.
# This prevents old or duplicate chunks from remaining.
#Checks if collection with same name already exists and then deletes previous collection
existing_collections = client.list_collections()

existing_names = [
    item.name if hasattr(item, "name") else str(item)
    for item in existing_collections
]

if COLLECTION_NAME in existing_names:
    client.delete_collection(name=COLLECTION_NAME)

collection = client.create_collection(
    name=COLLECTION_NAME
)


# Used for normal Markdown documents.
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=100
)


document_ids = []
document_texts = []
document_metadata = []


# -------------------------------------------------
# Ingest normal Markdown documents
# -------------------------------------------------

for file_path in DATA_FOLDER.rglob("*.md"):
    print(f"Reading Markdown: {file_path}")

    text = file_path.read_text(encoding="utf-8")
    chunks = text_splitter.split_text(text)

    relative_path = file_path.relative_to(DATA_FOLDER)

    if len(relative_path.parts) > 1:
        department = relative_path.parts[0].lower()
    else:
        department = "general"

    for chunk_number, chunk in enumerate(chunks):
    #Craete a unique document id
        document_id = (
            f"markdown:"
            f"{relative_path.as_posix()}:"
            f"{chunk_number}"
        )

        document_ids.append(document_id)
        document_texts.append(chunk)

        document_metadata.append({
            "source": relative_path.as_posix(),
            "department": department,
            "record_type": "document_chunk",
            "chunk_number": chunk_number
        })


# -------------------------------------------------
# Ingest HR CSV
# One employee row = one Chroma document
# -------------------------------------------------

if HR_CSV_PATH.exists():

    print(f"Reading employee records: {HR_CSV_PATH}")

    with HR_CSV_PATH.open(
        mode="r",
        encoding="utf-8-sig",
        newline=""
    ) as csv_file:

        reader = csv.DictReader(csv_file)

        for row in reader:

            employee_id = row["employee_id"].strip().upper()
            full_name = row["full_name"].strip()

            # Convert this employee's complete row into searchable text.
            employee_text = "\n".join(
                f"{column.replace('_', ' ').title()}: {value}"
                for column, value in row.items()
            )

            document_ids.append(
                f"employee:{employee_id}"
            )

            document_texts.append(employee_text)

            document_metadata.append({
                # "hr" means this is protected HR information.
                "department": "hr",

                "record_type": "employee",
                "employee_id": employee_id,
                "full_name": full_name,

                # This is the employee's actual working department.
                "employee_department": row[
                    "department"
                ].strip(),

                "job_role": row["role"].strip(),
                "source": "hr/hr_data.csv"
            })

else:
    print(f"HR CSV not found: {HR_CSV_PATH}")


# -------------------------------------------------
# Store everything in ChromaDB
# -------------------------------------------------

if not document_texts:
    print("No documents were found.")

else:
    collection.add(
        ids=document_ids,
        documents=document_texts,
        metadatas=document_metadata
    )

    print(
        f"Successfully ingested "
        f"{len(document_texts)} documents."
    )

    print(
        f"Total documents in ChromaDB: "
        f"{collection.count()}"
    )