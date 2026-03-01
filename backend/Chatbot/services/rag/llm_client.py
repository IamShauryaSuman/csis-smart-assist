from Chatbot.services.rag.memory import get_gemini_client

def generate_answer(query: str, relevant_chunks: list, memory_context: list = None) -> str:
    """Generates an answer using Gemini given doc chunks and memory context."""
    gemini_client = get_gemini_client()
    context = '\n'.join(relevant_chunks) if relevant_chunks else "No specific documents found."
    
    chat_history = ""
    if memory_context:
        chat_history = f"\nRelevant Past Conversations:\n{chr(10).join(memory_context)}\n---\n"

    prompt_template = f"""
Answer the question based only on the provided context and the chat history. 
If you cannot answer the question from the context, say "I'm sorry, I don't know based on the provided documents".
If your answer contains or references a link from the context, ALWAYS include the link in your response and format it cleanly as a Markdown link.

Context Documents:
---
{context}
---
{chat_history}
Question:
---
{query}
---
"""
    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_template
        )
        return response.text
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return "Sorry, I am currently unable to answer your query due to an internal error."
