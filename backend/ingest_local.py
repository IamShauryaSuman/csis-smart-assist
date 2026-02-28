import os
import argparse
from Chatbot.services.rag.drive_connector import extract_text
from Chatbot.services.rag.vector_store import chunk_text, embed, create_vector_store

def ingest_directory(directory_path: str):
    """Reads all PDF and TXT files in a directory and adds them to ChromaDB."""
    if not os.path.exists(directory_path):
        print(f"Error: Directory '{directory_path}' does not exist.")
        return

    all_chunks = []
    
    for filename in os.listdir(directory_path):
        filepath = os.path.join(directory_path, filename)
        if not os.path.isfile(filepath):
            continue
            
        print(f"Processing: {filename}...")
        
        # Determine mime-type based on extension
        mime_type = "text/plain"
        if filename.lower().endswith('.pdf'):
            mime_type = "application/pdf"
        elif filename.lower().endswith('.docx'):
            mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            
        with open(filepath, 'rb') as f:
            file_content = f.read()
            
        text = extract_text(file_content, mime_type)
        if not text:
            print(f"Warning: No text extracted from {filename}")
            continue
            
        chunks = chunk_text(text, chunk_size=30)
        all_chunks.extend(chunks)
        print(f" -> Extracted {len(chunks)} chunks from {filename}")
        
    if all_chunks:
        print(f"\nEmbedding {len(all_chunks)} total chunks. This might take a moment...")
        embeddings = embed(all_chunks)
        create_vector_store(embeddings, all_chunks)
        print("Successfully embedded and stored all documents in RAG_db!")
    else:
        print("No valid text found to embed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest local documents into the Chatbot Vector Store.")
    parser.add_argument("--dir", type=str, default="./data", help="Directory containing PDF/DOCX/TXT files")
    args = parser.parse_args()
    
    ingest_directory(args.dir)
