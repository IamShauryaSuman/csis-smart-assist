import re
user_message = "what is his VoIP number?"
conversation_context = "User: What is Bharat Sir's chamber number\nAssistant: According to the provided context documents, Bharat M. Deshpande ... has his office located at D-257 ... So, Bharat Sir's chamber number is D-257."
full_text = conversation_context + " " + user_message

keywords = [w for w in set(re.findall(r'\b[a-zA-Z]{4,}\b', full_text)) 
            if w.lower() not in {"what", "when", "where", "which", "who", "whom", "whose", "why", "how", "this", "that", "these", "those", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did", "will", "would", "shall", "should", "can", "could", "may", "might", "must", "about", "above", "across", "after", "against", "along", "among", "around", "at", "before", "behind", "below", "beneath", "beside", "between", "beyond", "but", "by", "concerning", "considering", "despite", "down", "during", "except", "for", "from", "in", "inside", "into", "like", "near", "of", "off", "on", "onto", "out", "outside", "over", "past", "regarding", "round", "since", "through", "throughout", "till", "to", "toward", "under", "underneath", "until", "up", "upon", "with", "within", "without", "number", "email", "office", "chamber", "room", "department", "csis", "bits", "pilani", "user", "assistant", "provided", "context", "documents", "according", "located"}]
print("Keywords:", keywords)
