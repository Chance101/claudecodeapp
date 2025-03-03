from flask import Flask, request, jsonify, render_template
import os
import json
import requests
import datetime
from dotenv import load_dotenv
from flask_cors import CORS

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Store conversation history
conversations = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        print(f"Received API request: {request.remote_addr}, Headers: {dict(request.headers)}")
        data = request.json
        if not data:
            print(f"No JSON data in request: {request.data}")
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
            print("API key missing (E1000)")
            return jsonify({"error": "E1000: API key not configured"}), 500
        
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
        except requests.exceptions.ConnectionError as e:
            print(f"API connection error (E1001): {str(e)}")
            return jsonify({"error": "E1001: Failed to connect to the AI service. Network connection issue."}), 500
        except requests.exceptions.Timeout as e:
            print(f"API timeout error (E1002): {str(e)}")
            return jsonify({"error": "E1002: Request to AI service timed out. Please try again."}), 500
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if hasattr(e, 'response') and e.response is not None else "unknown"
            print(f"API HTTP error (E1003): Status {status_code} - {str(e)}")
            return jsonify({"error": f"E1003: AI service returned error {status_code}. Please try again."}), 500
        except requests.exceptions.RequestException as e:
            print(f"API request error (E1004): {str(e)}")
            return jsonify({"error": "E1004: Failed to connect to the AI service. Please try again."}), 500
        
        try:
            response_data = response.json()
        except ValueError:
            print(f"Invalid JSON response (E2001): {response.text}")
            return jsonify({"error": "E2001: Invalid JSON response from AI service"}), 500
        
        # Check for expected response format
        if "content" not in response_data:
            print(f"Missing 'content' field in API response (E2002): {response_data}")
            return jsonify({"error": "E2002: Unexpected response format from AI service (missing 'content')"}), 500
        elif not response_data["content"]:
            print(f"Empty 'content' field in API response (E2003): {response_data}")
            return jsonify({"error": "E2003: Empty response content from AI service"}), 500
            
        try:
            assistant_message = response_data["content"][0]["text"]
        except (KeyError, IndexError) as e:
            print(f"Error extracting response text (E2004): {str(e)}, Response data: {response_data}")
            return jsonify({"error": "E2004: Unable to extract response text from AI service"}), 500
        
        # Add assistant response to conversation history
        conversations[conversation_id].append({"role": "assistant", "content": assistant_message})
        
        return jsonify({
            "response": assistant_message,
            "conversation_id": conversation_id
        })
        
    except json.JSONDecodeError as e:
        print(f"JSON decode error (E3001): {str(e)}")
        return jsonify({"error": "E3001: Invalid request data format"}), 400
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        print(f"Unexpected error (E9999): {str(e)}\n{error_traceback}")
        return jsonify({"error": "E9999: An unexpected server error occurred"}), 500

# Add a health check endpoint for debugging
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "ok",
        "timestamp": str(datetime.datetime.now()),
        "environment": os.environ.get('FLASK_ENV', 'development')
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)