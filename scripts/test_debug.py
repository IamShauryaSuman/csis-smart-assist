import re
user_message = "What is Siddharth Sir's Email Id"
keywords = [w for w in set(re.findall(r'\b[a-zA-Z]{4,}\b', user_message)) 
            if w.lower() not in {"what", "when", "where", "which", "who", "whom", "whose", "why", "how", "this", "that", "these", "those", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did", "will", "would", "shall", "should", "can", "could", "may", "might", "must", "about", "above", "across", "after", "against", "along", "among", "around", "at", "before", "behind", "below", "beneath", "beside", "between", "beyond", "but", "by", "concerning", "considering", "despite", "down", "during", "except", "for", "from", "in", "inside", "into", "like", "near", "of", "off", "on", "onto", "out", "outside", "over", "past", "regarding", "round", "since", "through", "throughout", "till", "to", "toward", "under", "underneath", "until", "up", "upon", "with", "within", "without", "number", "email", "office", "chamber", "room", "department", "csis", "bits", "pilani"}]

print("Keywords:", keywords)
