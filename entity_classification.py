from transformers import pipeline

# Initialize the zero-shot classification model
classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

def classify_entity(entity_name, candidate_labels):
    """
    Classifies an entity into one of the provided categories using zero-shot classification.
    """
    result = classifier(entity_name, candidate_labels)
    return result

# --- Example Usage ---
if __name__ == '__main__':
    entity_name = "Global Health Foundation"
    candidate_labels = ["Corporation", "Non-profit", "Shell Company", "Government Agency"]
    
    classification_result = classify_entity(entity_name, candidate_labels)
    print("Classification Result:", classification_result)