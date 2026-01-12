from graph import app
from langchain_core.messages import HumanMessage

if __name__ == '__main__':
    print('---Inflx Social-to-Lead Agentic Workflow is running---')
    print('Type "quit" to exit.')
    
    # Initialize state
    current_state = {'messages': [], 'user_info': {}, 'intents': '', 'lead_captured': False}
    
    while True:
        user_input = input('\nYou: ')
        if user_input.lower() in ['quit', 'exit']:
            break
        current_state['messages'].append(HumanMessage(content=user_input))
        output_state = app.invoke(current_state)
        ai_message = output_state['messages'][-1]
        print(f'Agent: {ai_message.content}')
        current_state = output_state