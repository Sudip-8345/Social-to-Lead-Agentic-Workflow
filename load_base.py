import json
from langchain_core.documents import Document

def load_knowledge_base():
    with open('knowledge_base.json','r') as f:
        data = json.load(f)
    
    docs = []
    for prod in data['Products']:
        content = f"Plan: {prod['plan_name']}\nPrice: {prod['price']}\nFeatures: {', '.join(prod['features'])}"
        docs.append(Document(page_content=content))
    
    policy_txt = "Company Policies:\n" + "\n".join(data['Policies'])
    docs.append(Document(page_content=policy_txt))

    return docs