#Find files under data/
#Extract thei rtext
#Split the text into 700 character chunks with overlap 
#Attach metadata to every chunk such as department and source
#Add chunks to chroma collectoin 

#Default embedding model used by ChromaDB is all-MiniLM-L6-v2
from pathlib import Path
import chromadb
import csv
from langchain_text_splitters import RecursiveCharacterTextSplitter

client = chromadb.PersistentClient(path="chroma_db")

collection = client.get_or_create_collection(
    name="company_documents"
)

#Create a text splitter that breaks long text into smaller chunks 
#Where each chink size is 800 characters and chunk overlap is 100 characters
#This text splitter tries to split at natural boundaries like ends of paragraphs or sentences
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=100
)

data_folder = Path("data")

chunk_ids = []
chunk_texts = []
chunk_metadata = []

#This loop goes through each md file in the data folder
#It splits the text in each file into chunks and labels it 

for file_path in data_folder.rglob("*.md"):
    print(f"Reading: {file_path}")

    text = file_path.read_text(encoding="utf-8")
    chunks = text_splitter.split_text(text)

    # If file is data/hr/policy.md, department becomes "hr"
    #Get the file path without data/ part so hr/policy.md
    relative_path = file_path.relative_to(data_folder)

    #If file is within a sub folder then use the first folder name
    if len(relative_path.parts) > 1:
        department = relative_path.parts[0].lower()
    else:
        department = "general"

    #Go through each chunk
    #Enumerate gives each chunk a number from 0 
    for chunk_number, chunk in enumerate(chunks):
        # Every chunk needs a unique ID
        chunk_id = f"{relative_path}-{chunk_number}"

        chunk_ids.append(chunk_id)
        chunk_texts.append(chunk)

        chunk_metadata.append({
            "source": str(relative_path),
            "department": department,
            "chunk_number": chunk_number
        })

    #if no chunks were collected, then this is printed
if not chunk_texts:
    print("No .md files found inside the data folder.")

    #upsert stores the chunks into the collection with Ids and metadata
    #Chroma creates embeddings for the text using collection's embedding function 
else:
    # Chroma automatically creates embeddings and stores everything
    collection.upsert(
        ids=chunk_ids,
        documents=chunk_texts,
        metadatas=chunk_metadata        
    )

print(f"Successfully ingested {len(chunk_texts)} chunks.")
print(f"Total chunks in ChromaDB: {collection.count()}")