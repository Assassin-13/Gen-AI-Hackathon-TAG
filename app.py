import requests
import json
import re
import spacy
import csv
from fuzzywuzzy import fuzz
from flask import Flask, request, jsonify
from flask_cors import CORS
from transformers import pipeline

# Load NLP Model
nlp = spacy.load("en_core_web_sm")

# Load Zero-Shot Classification Model
classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli", device=-1)

def classify_entity(entity_name, candidate_labels):
    """
    Classifies an entity into one of the provided categories using zero-shot classification.
    """
    result = classifier(entity_name, candidate_labels)
    return result

# External API Endpoints (for enrichment)
OPEN_CORPORATES_API = "https://api.opencorporates.com/v0.4/companies/search?q={}" 
SEC_EDGAR_API = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company={}" 
OFAC_SANCTIONS_LIST = "https://www.treasury.gov/resource-center/sanctions/SDN-List/Pages/default.aspx"

# Initialize Flask API
app = Flask(__name__)
CORS(app)

# Define valid entity types
VALID_ENTITY_TYPES = {"ORG", "PERSON"}

# Define a set of generic locations and irrelevant terms to exclude
EXCLUDED_TERMS = {
    "Panama", "Switzerland", "Geneva", "George Town", "Cayman Islands", "USA", "UK", "Europe", "Asia", "Africa", "America", "City", "State",
    "IBAN", "Rue du Marché", "N/A Transaction Type: Wire Transfer Reference", "Cayman Islands Tax", "Sender IP", "Amount", "Currency Exchange", "Reference"
}

# Extract entities from text
def extract_entities(text):
    """Extracts relevant entities using NLP and filters out irrelevant locations."""
    doc = nlp(text)
    entities = []
    for ent in doc.ents:
        if ent.label_ in VALID_ENTITY_TYPES and ent.text not in EXCLUDED_TERMS:
            # Remove short entities and numeric-only values
            if len(ent.text) > 3 and not ent.text.isnumeric():
                entities.append(ent.text)
    return list(set(entities))  # Remove duplicates

def fuzzy_match(name, dataset):
    """Fuzzy match entity name against a dataset."""
    for entry in dataset:
        if fuzz.partial_ratio(name.lower(), entry.lower()) > 85:
            return True
    return False

def fetch_risk_data(entity_name):
    """Fetch entity risk data from external sources."""
    risk_score = 0.1  # Default low risk
    sources = []
    
    # Check OpenCorporates
    response = requests.get(OPEN_CORPORATES_API.format(entity_name))
    if response.status_code == 200 and "results" in response.json():
        sources.append("OpenCorporates")
        risk_score += 0.2
    
    # Check SEC EDGAR filings
    response = requests.get(SEC_EDGAR_API.format(entity_name))
    if response.status_code == 200:
        sources.append("SEC EDGAR")
        risk_score += 0.2
    
    # Check OFAC Sanctions List (Dummy Check)
    if fuzzy_match(entity_name, ["Sanctioned Entity A", "Sanctioned Entity B"]):
        sources.append("OFAC Sanctions List")
        risk_score += 0.5
    
    confidence_score = min(1.0, risk_score)
    return {
        "Entity": entity_name,
        "Risk Score": risk_score,
        "Supporting Evidence": sources,
        "Confidence Score": confidence_score
    }

@app.route('/analyze', methods=['POST'])
def analyze_transaction():
    """API Endpoint for transaction analysis."""
    data = request.json
    transaction_id = data.get("Transaction ID", "Unknown")
    text = data.get("Transaction Details", "")
    
    entities = extract_entities(text)
    entity_classifications = []
    
    for entity_name in entities:
        candidate_labels = ["Corporation", "Non-profit", "Shell Company", "Government Agency"]
        classification_result = classify_entity(entity_name, candidate_labels)
        entity_classifications.append({"Entity": entity_name, "Classification": classification_result})
        print("Classification Result:", classification_result)
    
    results = [fetch_risk_data(entity) for entity in entities]
    
    return jsonify({"Transaction ID": transaction_id, "Entities": results, "Classifications": entity_classifications})

if __name__ == '__main__':
    app.run(debug=True)
