from flask import Flask, request, jsonify, render_template
import os
import json
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Store conversation history
conversations = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '')
    conversation_id = data.get('conversation_id', 'default')
    
    if not user_message:
        return jsonify({"error": "No message provided"}), 400
    
    # Initialize conversation history if it doesn't exist
    if conversation_id not in conversations:
        conversations[conversation_id] = []
    
    # Add user message to history
    conversations[conversation_id].append({"role": "user", "content": user_message})
    
    # Create messages array for Claude
    messages = conversations[conversation_id].copy()
    
    # If this is the first message, add system prompt for customer service
    if len(messages) == 1:
        messages.insert(0, {
            "role": "system",
            "content": """You are a helpful customer service assistant. Your job is to:
            1. Answer questions about products and services
            2. Help troubleshoot issues
            3. Process returns and exchanges
            4. Provide information about orders
            5. Be friendly, professional, and concise
            6. Escalate to a human agent when necessary
            
            Always maintain a helpful and friendly tone. If you don't know the answer to a question, 
            admit it rather than making up information.
            """
        })
    
    # Call Claude API directly
    headers = {
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
        "x-api-key": os.getenv("ANTHROPIC_API_KEY")
    }
    
    api_url = "https://api.anthropic.com/v1/messages"
    payload = {
        "model": "claude-3-sonnet-20240229",
        "max_tokens": 1000,
        "temperature": 0.7,
        "messages": messages
    }
    
    response = requests.post(api_url, headers=headers, json=payload)
    
    if response.status_code != 200:
        return jsonify({"error": f"API call failed with status {response.status_code}: {response.text}"}), 500
    
    response_data = response.json()
    assistant_message = response_data["content"][0]["text"]
    
    # Add assistant response to conversation history
    conversations[conversation_id].append({"role": "assistant", "content": assistant_message})
    
    return jsonify({
        "response": assistant_message,
        "conversation_id": conversation_id
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)