import os
import json
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") # Use service role for admin read access

if not url or not key:
    print("Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")
    exit(1)

supabase: Client = create_client(url, key)

def fetch_and_format_data(output_file="data/dataset.jsonl"):
    """
    Fetches historical interaction data from Supabase and formats it into JSONL
    for fine-tuning Llama 3.
    
    Expected format for Llama-3 instruction tuning:
    {"text": "<|start_header_id|>system<|end_header_id|>\n\nYou are CSIS SmartAssist...<|eot_id|><|start_header_id|>user<|end_header_id|>\n\nUSER_QUERY<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\nASSISTANT_RESPONSE<|eot_id|>"}
    """
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    print("Fetching data from Supabase...")
    # NOTE: Adjust 'messages' and columns based on your actual Supabase schema
    # Here we assume a table structure with 'role' (user/assistant) and 'content'
    # grouped by 'session_id'.
    try:
        # Example query - you will likely need to adjust this to match your schema
        # response = supabase.table('messages').select('*').order('created_at').execute()
        # messages = response.data
        messages = [] # Placeholder
        print("Please configure the Supabase query in scripts/generate_dataset.py to match your schema.")
        
        # --- SYNTHETIC EXAMPLE DATA ---
        # Since we don't have the exact schema, we will generate some sample data
        # demonstrating intent routing and RAG style answers for the CSIS department.
        sample_data = [
            {
                "instruction": "I need to book the systems lab for a makeup class tomorrow from 2 to 4 pm.",
                "response": '{"intent": "calendar_query", "action": "book_lab", "lab": "systems_lab", "time": "14:00-16:00"}'
            },
            {
                "instruction": "What is the syllabus for CS F211?",
                "response": '{"intent": "department_query", "topic": "syllabus", "course": "CS F211"}'
            },
            {
                "instruction": "How does quicksort work?",
                "response": '{"intent": "general_query"}\nQuicksort is a divide-and-conquer algorithm...'
            }
        ]
        
        system_prompt = "You are CSIS SmartAssist, an AI for the CSIS Department at BITS Pilani Goa. Route intents or answer questions."
        
        with open(output_file, 'w') as f:
            for item in sample_data:
                # Format into Llama 3 ChatML-like template
                text = f"<|start_header_id|>system<|end_header_id|>\n\n{system_prompt}<|eot_id|>"
                text += f"<|start_header_id|>user<|end_header_id|>\n\n{item['instruction']}<|eot_id|>"
                text += f"<|start_header_id|>assistant<|end_header_id|>\n\n{item['response']}<|eot_id|>"
                
                f.write(json.dumps({"text": text}) + '\n')
                
        print(f"Successfully generated {len(sample_data)} training examples at {output_file}")
        
    except Exception as e:
        print(f"Error fetching data: {e}")

if __name__ == "__main__":
    fetch_and_format_data()
