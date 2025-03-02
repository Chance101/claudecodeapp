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
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
            
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
        
        # Check if API key is available
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return jsonify({"error": "API key not configured"}), 500
        
        # Call Claude API directly
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        api_url = "https://api.anthropic.com/v1/messages"
        payload = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 1000,
            "temperature": 0.7,
            "messages": messages
        }
        
        try:
            # Print request info but hide the API key
            safe_headers = headers.copy()
            safe_headers["x-api-key"] = "..." + api_key[-4:]
            print(f"API Request: URL={api_url}, Headers={safe_headers}, Payload={json.dumps(payload)}")
            response = requests.post(api_url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()  # Raise an exception for 4XX/5XX responses
        except requests.exceptions.RequestException as e:
            print(f"API request error: {str(e)}")
            return jsonify({"error": "Failed to connect to the AI service. Please try again."}), 500
        
        try:
            response_data = response.json()
        except ValueError:
            print(f"Invalid JSON response: {response.text}")
            return jsonify({"error": "Invalid response from AI service"}), 500
        
        # Check for expected response format
        if "content" not in response_data or not response_data["content"]:
            print(f"Unexpected API response format: {response_data}")
            return jsonify({"error": "Unexpected response format from AI service"}), 500
            
        assistant_message = response_data["content"][0]["text"]
        
        # Add assistant response to conversation history
        conversations[conversation_id].append({"role": "assistant", "content": assistant_message})
        
        return jsonify({
            "response": assistant_message,
            "conversation_id": conversation_id
        })
        
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return jsonify({"error": "An unexpected error occurred"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)