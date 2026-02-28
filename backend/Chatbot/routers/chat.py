from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict
from Chatbot.services.rag.vector_store import retrieve_relevant_chunks
from Chatbot.services.rag.llm_client import generate_answer
from Chatbot.services.rag.memory import retrieve_memory, add_to_memory

router = APIRouter()

class ChatRequest(BaseModel):
    query: str
    user_id: str

class ChatResponse(BaseModel):
    answer: str

# In-memory sliding window for the session. 
# A real app might store this in Redis or SQLite temporarily.
sliding_window: Dict[str, List[Dict[str, str]]] = {}
WINDOW_SIZE = 5

@router.post("/", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    query = request.query
    user_id = request.user_id
    
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
        
    try:
        # 1. Retrieve Doc context from the main RAG DB
        doc_chunks = retrieve_relevant_chunks(query, collection_name="RAG_db", top_k=5)
        
        # 2. Retrieve long-term Memory context specific to the user
        memory_chunks = retrieve_memory(user_id, query, top_k=3)
        
        # 3. Add sliding window to memory context
        history = sliding_window.get(user_id, [])
        history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])
        if history_text:
            memory_chunks.append(f"Recent interactions:\n{history_text}")
            
        # 4. Generate Answer using Gemini
        answer = generate_answer(query, doc_chunks, memory_chunks)
        
        # 5. Update sliding window
        history.append({"role": "user", "content": query})
        history.append({"role": "assistant", "content": answer})
        
        # 6. Summarize oldest messages into memory DB if window exceeded
        if len(history) > WINDOW_SIZE * 2:
            oldest_pair = history[:2]
            history = history[2:]
            text_to_summarize = "\n".join([f"{msg['role']}: {msg['content']}" for msg in oldest_pair])
            # Async background task could be better here, but doing it sync for MVP
            add_to_memory(user_id, text_to_summarize)
            
        sliding_window[user_id] = history
        
        return {"answer": answer}
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail="An error occurred processing the chat request")
