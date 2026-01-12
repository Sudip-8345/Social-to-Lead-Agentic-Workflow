import json
import re
from agents import AgentState
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from langchain_core.tools import tool
from config import llm

# ===============Mock Lead Capture Tool ==================
@tool
def mock_lead_capture(name: str, email: str, platform: str):
    '''
    Mock backend API that should only be called when all details are collected.
    '''
    print(f'[TOOL] Lead captured successfully: {name}, {email}, {platform}')
    return f"Lead captured: {name}, {email}, {platform}"
  
def is_valid_email(email: str) -> bool:
    """Check if email has @ and . after @"""
    if '@' not in email:
        return False
    parts = email.split('@')
    if len(parts) != 2:
        return False
    domain = parts[1]
    return '.' in domain and len(domain) > 2

# ===============Intent Classifier Tool ==================
def intent_classifier(state: AgentState) -> dict:
    '''This function classifies user messages into: Greeting, Inquiry, Lead.'''
    system_prompt = '''
    You are an intent classifier for Inflx. Classify the user's intent into one of the following categories:
    - GREETING: Casual hello or hi messages or bye.
    - INQUIRY: Questions about products, pricing, features, or policies.
    - LEAD: User wants to sign up or provide contact details showing interest in buying some plan or trying the product.
    
    Respond with ONLY one word: GREETING, INQUIRY, or LEAD. No other text.
    '''
    message = [SystemMessage(content=system_prompt)] + state['messages']
    response = llm.invoke(message)
    
    # Extract intent keyword from response
    intent_text = response.content.strip().upper()
    if "LEAD" in intent_text:
        intent = "LEAD"
    elif "INQUIRY" in intent_text:
        intent = "INQUIRY"
    else:
        intent = "GREETING"
    
    return {'intents': intent}

# ===============Helper to parse JSON from LLM response ==================
def extract_json(text: str) -> dict:
    '''Extract JSON from LLM response, handling markdown code blocks.'''
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if json_match:
        text = json_match.group(1)
    
    json_match = re.search(r'\{[\s\S]*\}', text)
    if json_match:
        text = json_match.group(0)
    
    return json.loads(text)

# ===============Lead Capture Tool ==================
def lead_capture_agent(state: AgentState) -> dict:
    '''This function collects name, email, platform from user messages and calls mock_lead_capture API.'''
    user_info = state.get('user_info', {})
    required_fields = ['name', 'email', 'platform']
    missing_fields = [field for field in required_fields if field not in user_info or not user_info[field]]
    
    if not missing_fields:
        result = mock_lead_capture.invoke({
            'name': user_info['name'],
            'email': user_info['email'],
            'platform': user_info['platform']
        })
        return {
            'messages': [AIMessage(content=f"Thanks {user_info['name']} for your interest!\n{result}")],
            'lead_captured': True
        }
    
    system_prompt = f'''
    You are a sales agent for Inflx by ServiceHive. Your goal is to collect: Name, Email, and Content Platform (YouTube, Instagram, etc).
    
    Current collected info: {json.dumps(user_info)}
    Missing info: {json.dumps(missing_fields)}
    
    1. Analyze the LAST message. If the user provided any of the missing info, extract it.
    2. If info is still missing, politely ask for ONE piece of missing information at a time.
    3. Return your response in this exact JSON format (no markdown, just raw JSON):
    {{
        "collected": {{ "field_name": "value" }},
        "response_text": "Your message to the user"
    }}
    
    Example: {{"collected": {{"name": "John"}}, "response_text": "Nice to meet you John! What's your email address?"}}
    '''
    messages = [
        SystemMessage(content=system_prompt),
        *state['messages']
    ]
    response = llm.invoke(messages)
    
    try:
        data = extract_json(response.content)
        new_info = data.get('collected', {})
        response_text = data.get('response_text', '')
        
        # Filter empty values
        new_info = {k: v for k, v in new_info.items() if v}
        
        # Validate email format before accepting
        if 'email' in new_info:
            email = new_info['email']
            if not is_valid_email(email):
                return {
                    'messages': [AIMessage(content=f"Hmm, '{email}' doesn't look like a valid email. Could you please provide a valid email address (e.g., name@example.com)?")],
                    'user_info': user_info
                }
        
        updated_user_info = {**user_info, **new_info}
        
        return {
            'messages': [AIMessage(content=response_text)],
            'user_info': updated_user_info
        }
    except Exception as e:
        print(f"[DEBUG] JSON parse error: {e}, Response: {response.content}")
        return {
            'messages': [AIMessage(content="I'd love to help you get started! Could you please tell me your name?")]
        }
# ===============Generic Responder Tool ================== 
def generic_responder(state: AgentState) -> dict:
    return {'messages': llm.invoke(state['messages'])}