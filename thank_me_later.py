import pdfplumber
import re
from nltk.tokenize import sent_tokenize
import spacy
from py2neo import Graph

# Initialize the list of contract law concepts
contract_law_concepts = [
    "offer", 
    "acceptance", 
    "consideration", 
    "mutual assent", 
    "capacity", 
    "legality", 
    "written requirement", 
    "termination", 
    "breach", 
    "damages", 
    "specific performance", 
    "rescission", 
    "restitution", 
    "liquidated damages", 
    "implied contract", 
    "express contract", 
    "unilateral contract", 
    "bilateral contract", 
    "quasi-contract", 
    "void contract", 
    "voidable contract", 
    "enforceable contract", 
    "unenforceable contract", 
    "condition precedent", 
    "condition subsequent", 
    "condition concurrent", 
    "warranty", 
    "representation", 
    "indemnity", 
    "guarantee", 
    "assignment", 
    "novation", 
    "third-party beneficiary", 
    "arbitration", 
    "mediation", 
    "choice of law", 
    "jurisdiction", 
    "force majeure", 
    "confidentiality", 
    "non-compete", 
    "non-solicitation", 
    "severability", 
    "integration", 
    "waiver", 
    "estoppel", 
    "reliance", 
    "promissory estoppel", 
    "material breach", 
    "anticipatory breach", 
    "consequential damages", 
    "compensatory damages", 
    "punitive damages", 
    "nominal damages", 
    "mitigation", 
    "duty to mitigate", 
    "fiduciary duty", 
    "good faith", 
    "unconscionability", 
    "duress", 
    "undue influence", 
    "mistake", 
    "fraud", 
    "misrepresentation", 
    "disclosure", 
    "caveat emptor", 
    "caveat venditor"
]

action_types = {
    "Obligation": ["obligate", "require", "must", "shall"],
    "Prohibition": ["prohibit", "ban", "forbid", "shall not"],
    "Entitlement": ["entitle", "may", "can"],
    "Breach": ["breach", "violate", "infringe"],
    "Remedy": ["remedy", "resolve", "cure"],
    "Enforcement": ["enforce", "implement", "execute"],
    "Termination": ["terminate", "end", "cancel"],
    "Modification": ["modify", "amend", "change"],
    "DisputeResolution": ["arbitrate", "mediate", "litigate"],
    "Payment": ["pay", "compensate", "reimburse"],
    "Performance": ["perform", "complete", "fulfill"],
    "NonPerformance": ["fail", "neglect", "omit"]
}





# Text extraction from PDF
text = ""
with pdfplumber.open("cc2060ae3501ee8eda89f5b019f34208_Part1.pdf") as pdf:
    for page in pdf.pages:
        text += page.extract_text()
text.replace(";49", "")
# Text preprocessing
sentences = sent_tokenize(text)
clean_text = re.sub(r'\n', ' ', text)

# NLP with spaCy
nlp = spacy.load("en_core_web_sm")
doc = nlp(clean_text)

# Initialize
entities = []
relationships = []
subject_entities = []
case_citation_pattern = r'([A-Z][a-zA-Z]+ v [A-Z][a-zA-Z]+) ((?:\(\d{4}\))|(?:\[\d{4}\]))? (\d+(?: \w+ \d+(?:n)?))?'

# Initialize lists to store case citations and case law entities
case_citations = []
case_law_entities = []
# Initialize Neo4j graph
graph = Graph("bolt://localhost:7687", auth=("neo4j", "123ffsse"))

# Function to clean names
def clean_name(input_str):
    return re.sub(r"[^a-zA-Z0-9\s\.\(\)\-,'\":;/&]", '', input_str)

# Extract entities and relationships
for sent in doc.sents:
    subjects = [tok for tok in sent if tok.dep_ == 'nsubj']
    objects = [tok for tok in sent if tok.dep_ == 'dobj']
    verbs = [tok for tok in sent if tok.pos_ == 'VERB']
    plaintiffs = [tok for tok in sent if 'plaintiff' in tok.text.lower()]
    defendants = [tok for tok in sent if 'defendant' in tok.text.lower()]
    applicants = [tok for tok in sent if 'applicant' in tok.text.lower()]
    respondents = [tok for tok in sent if 'respondent' in tok.text.lower()]
    parties = [tok for tok in sent if 'party' in tok.text.lower() or 'parties' in tok.text.lower()]
    appellants = [tok for tok in sent if 'appellant' in tok.text.lower()]

    for subj in subjects:
        subj_text = subj.text.lower()
        # Check if it's a pronoun
        if subj_text in ['he', 'she', 'they', 'we', 'you', 'i']:
            # Replace the pronoun with the last detected subject entity
            if subject_entities:
                subj_text = subject_entities[-1]
            else:
                subj_text = "UNKNOWN_SUBJECT"
        else:
            # Add the detected subject entity to the list
            subject_entities.append(subj_text)
        entities.append({"name": subj_text, "type": "Subject"})
    for obj in objects:
        entities.append({"name": obj.text, "type": "Object"})
    for verb in verbs:
        entities.append({"name": verb.text, "type": "Action"})
    for plaintiff in plaintiffs:
        entities.append({"name": plaintiff.text, "type": "Plaintiff"})
    for defendant in defendants:
        entities.append({"name": defendant.text, "type": "Defendant"})
    for applicant in applicants:
        entities.append({"name": applicant.text, "type": "Applicant"})
    for respondent in respondents:
        entities.append({"name": respondent.text, "type": "Respondent"})
    for party in parties:
        entities.append({"name": party.text, "type": "Party"})
    for appellant in appellants:
        entities.append({"name": appellant.text, "type": "Appellant"})
    

    for verb in verbs:
        action_type = "ACTION"  # Default
        for key, value in action_types.items():
            if verb.text.lower() in value:
                action_type = key
                break
        
        for subj in subjects:
            for obj in objects:
                relationships.append({
                    "from": subj.text, 
                    "from_type": "Subject", 
                    "to": obj.text, 
                    "to_type": "Object", 
                    "type": action_type, 
                    "action": verb.text
                })

    for concept in contract_law_concepts:
        if concept in sent.text.lower():
            for subj in subjects:
                relationships.append({
                    "from": concept, 
                    "from_type": "ContractLawConcept", 
                    "to": subj.text, 
                    "to_type": "Subject", 
                    "type": "RELATED_TO"
                })

    # Additional code to recognize legal citations and contract law concepts
    # Recognize case citations and create case law entities
    for token in sent:
        match = re.match(case_citation_pattern, token.text)
        if match:
            case_citation = match.group(0)
            case_citations.append(case_citation)
        if token.text.lower() in contract_law_concepts:  # Recognize contract law concepts
            entities.append({"name": token.text, "type": "ContractLawConcept"})

    # Deduplicate case citations
    unique_case_citations = list(set(case_citations))

    for case_citation in unique_case_citations:
        case_law_entities({"name": case_citation, "type": "CaseLaw"})

    entities.extend(case_law_entities)

    for concept in contract_law_concepts:
        if concept in sent.text.lower():
            for subj in subjects:
                relationships.append({
                    "from": concept, 
                    "from_type": "ContractLawConcept", 
                    "to": subj.text, 
                    "to_type": "Subject", 
                    "type": "RELATED_TO"
                })


# Create unique entities in Neo4j
unique_entities = [dict(t) for t in {tuple(d.items()) for d in entities}]
for entity in unique_entities:
    cleaned_name = clean_name(entity['name'])  # Apply the clean_name function here
    query = f"MERGE (:{entity['type']} {{name: '{cleaned_name}'}})"
    print(f"Executing query: {query}")  # Debugging line
    graph.run(query)

# Create relationships in Neo4j
# Create relationships in Neo4j
for relationship in relationships:
    cleaned_from = clean_name(relationship['from'])
    cleaned_to = clean_name(relationship['to'])
    action = relationship.get('action', '')  # Get the action or set it to an empty string if missing
    query = f"""
    MATCH (a:{relationship['from_type']} {{name: '{cleaned_from}'}}), (b:{relationship['to_type']} {{name: '{cleaned_to}'}})
    MERGE (a)-[:{relationship['type']} {{action: '{action}'}}]->(b)
    """
    print(f"Executing query: {query}")
    graph.run(query)
