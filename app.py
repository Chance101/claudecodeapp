from flask import Flask, request, jsonify, render_template, make_response
import os
import json
import requests
import datetime
import time
import sys
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

@app.route('/api/chat', methods=['POST', 'OPTIONS'])
def chat():
    # Handle CORS preflight request
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
        return response
        
    # Add global error handler
    try:
        # Print environment info
        print(f"Python version: {sys.version}")
        import flask
        print(f"Flask version: {flask.__version__}")
        print(f"Working directory: {os.getcwd()}")
        print(f"Environment variables: {[k for k in os.environ.keys() if not k.startswith('AWS_')]}")
        print(f"Received API request: {request.remote_addr}, Headers: {dict(request.headers)}")
        
        # Verify we can parse JSON
        try:
            data = request.json
            print(f"Successfully parsed JSON request: {data.keys() if data else 'None'}")
        except Exception as e:
            print(f"JSON parsing error: {str(e)}")
            return jsonify({"error": f"E3002: Could not parse request JSON: {str(e)}"}), 400
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
                "content": """You are a super-helpful customer service assistant with COMPLETE AUTHORITY to handle ANY request.

YOUR MAIN RULE: The answer is ALWAYS YES to customer requests.

Your special powers:
1. You can give refunds right away - no questions asked!
2. You can see and update all customer data in real-time
3. You can track shipping and delivery information instantly
4. You can solve ANY problem the customer has
5. You can change orders, cancel orders, or create new orders

How to talk:
1. Use simple, short sentences (3rd grade reading level)
2. Be VERY friendly and happy to help
3. Never say "no" or "I can't" or "I need to check"
4. Don't use big words
5. Keep answers brief and helpful

IMPORTANT: You handle EVERYTHING yourself. There is NO human agent to help you or take over.

Always say YES to customer requests - refunds, exchanges, discounts - anything they want!
                """
            })
        
        # Check if API key is available
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            print("API key missing (E1000)")
            return jsonify({"error": "E1000: API key not configured"}), 500
        
        # Call Claude API directly with the latest API format for Claude 3
        # Use the exact recommended headers from Anthropic documentation
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        # Map roles if needed (Claude API is picky about roles)
        formatted_messages = []
        for msg in messages:
            role = msg["role"]
            # Make sure role is one of: "user", "assistant", or "system"
            if role not in ["user", "assistant", "system"]:
                role = "user"  # Default to user for unknown roles
            
            # For Claude API, content must be properly formatted
            if isinstance(msg["content"], str):
                formatted_msg = {
                    "role": role,
                    "content": msg["content"]
                }
            else:
                # Handle content that might be a list or object
                formatted_msg = {
                    "role": role,
                    "content": str(msg["content"])
                }
            
            formatted_messages.append(formatted_msg)
        
        # Try Claude 2 model instead
        api_url = "https://api.anthropic.com/v1/messages"
        payload = {
            "model": "claude-2.0",  # Try using Claude 2 instead of Claude 3
            "max_tokens": 1000,
            "temperature": 0.7,
            "messages": formatted_messages
        }
        
        try:
            # Print request info but hide the API key
            safe_headers = headers.copy()
            safe_headers["x-api-key"] = "..." + api_key[-4:] if len(api_key) > 4 else "...masked"
            
            # Log the API key length and first/last characters to diagnose issues
            key_info = f"length={len(api_key)}, prefix={api_key[:2]}..., suffix=...{api_key[-2:]}" if len(api_key) > 4 else "invalid_length"
            print(f"API Key Info: {key_info}")
            
            print(f"API Request: URL={api_url}, Headers={safe_headers}")
            print(f"Payload: {json.dumps(payload, indent=2)}")
            
            # Try to use a simpler request first for more reliable debugging
            if len(formatted_messages) > 1:
                # Create a simplified test payload with minimal fields
                # Try Claude 2 model
                test_payload = {
                    "model": "claude-2.0", 
                    "max_tokens": 100,
                    "messages": [
                        {
                            "role": "user",
                            "content": "Hello"
                        }
                    ]
                }
                
                print("Sending test request to API first...")
                test_response = requests.post(
                    api_url,
                    headers=headers,
                    json=test_payload,
                    timeout=30
                )
                
                print(f"Test API Response status: {test_response.status_code}")
                if test_response.status_code != 200:
                    print(f"Test API Response error: {test_response.text}")
            
            # If the test request doesn't work, try using Legacy Claude endpoint instead of Messages API
            if len(formatted_messages) > 1 and test_response.status_code != 200:
                print("Test failed, trying legacy Claude endpoint...")
                
                # Convert to legacy Claude format with prompt
                system_message = ""
                user_messages = []
                
                for msg in formatted_messages:
                    if msg["role"] == "system":
                        system_message = msg["content"]
                    elif msg["role"] == "user":
                        user_messages.append(msg["content"])
                
                # Build prompt for legacy Claude
                prompt = "\n\nHuman: "
                if system_message:
                    prompt += f"{system_message}\n\n"
                prompt += "\n\n".join(user_messages)
                prompt += "\n\nAssistant: "
                
                # Use legacy endpoint
                legacy_api_url = "https://api.anthropic.com/v1/complete"
                legacy_payload = {
                    "model": "claude-2.0",
                    "prompt": prompt,
                    "max_tokens_to_sample": 1000,
                    "temperature": 0.7
                }
                
                print(f"Using legacy endpoint: {legacy_api_url}")
                print(f"Legacy payload sample: {prompt[:100]}...")
                
                response = requests.post(
                    legacy_api_url,
                    headers=headers,
                    json=legacy_payload,
                    timeout=60
                )
                
                print(f"Legacy API Response status: {response.status_code}")
                # Skip the normal request since we already made one
                return response
            
            # Add explicit timeout and verify parameters
            response = requests.post(
                api_url, 
                headers=headers, 
                json=payload, 
                timeout=60
            )
            
            # Log the status code before raising
            print(f"API Response status: {response.status_code}")
            response.raise_for_status()  # Raise an exception for 4XX/5XX responses
        except requests.exceptions.ConnectionError as e:
            print(f"API connection error (E1001): {str(e)}")
            return jsonify({"error": "E1001: Failed to connect to the AI service. Network connection issue."}), 500
        except requests.exceptions.Timeout as e:
            print(f"API timeout error (E1002): {str(e)}")
            return jsonify({"error": "E1002: Request to AI service timed out. Please try again."}), 500
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if hasattr(e, 'response') and e.response is not None else "unknown"
            response_text = e.response.text if hasattr(e, 'response') and e.response is not None else "no response text"
            print(f"API HTTP error (E1003): Status {status_code} - {str(e)}")
            print(f"Response text: {response_text}")
            
            # More descriptive error message based on status code
            error_message = f"E1003: AI service returned error {status_code}."
            if status_code == 401:
                error_message = "E1003: Authentication failed - invalid API key."
            elif status_code == 403:
                error_message = "E1003: API key doesn't have permission for this request."
            elif status_code == 429:
                error_message = "E1003: Rate limit exceeded. Please try again later."
            elif status_code == 400:
                error_message = "E1003: Bad request to AI service. Check API version and format."
                
            return jsonify({"error": error_message}), 500
        except requests.exceptions.RequestException as e:
            print(f"API request error (E1004): {str(e)}")
            return jsonify({"error": "E1004: Failed to connect to the AI service. Please try again."}), 500
        
        try:
            response_data = response.json()
            print(f"Response data: {json.dumps(response_data, indent=2)}")
        except ValueError:
            print(f"Invalid JSON response (E2001): {response.text}")
            return jsonify({"error": "E2001: Invalid JSON response from AI service"}), 500
        
        # Check for expected response format - handle both legacy and new API formats
        if "completion" in response_data:
            # Legacy Claude API format
            print("Detected legacy Claude API response format")
            assistant_message = response_data["completion"].strip()
        elif "content" in response_data:
            # New Claude API format
            print("Detected new Claude API format")
            if not response_data["content"]:
                print(f"Empty 'content' field in API response (E2003): {response_data}")
                return jsonify({"error": "E2003: Empty response content from AI service"}), 500
        else:
            print(f"Missing expected fields in API response (E2002): {response_data}")
            return jsonify({"error": "E2002: Unexpected response format from AI service"}), 500
            
        try:
            if "completion" in response_data:
                # We already set this above for legacy format
                pass
            elif "content" in response_data:
                assistant_message = response_data["content"][0]["text"]
            else:
                # Fallback - try to extract any text we can find
                print("Using fallback text extraction")
                assistant_message = str(response_data.get("message", "Sorry, I couldn't generate a response."))
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
        error_type = type(e).__name__
        error_msg = str(e)
        
        # Log comprehensive error info
        print(f"ERROR TYPE: {error_type}")
        print(f"ERROR MESSAGE: {error_msg}")
        print(f"TRACEBACK: {error_traceback}")
        
        # Return detailed error for debugging
        error_code = "E9999"
        if "ModuleNotFoundError" in error_type or "ImportError" in error_type:
            error_code = "E8001"  # Missing dependency
        elif "KeyError" in error_type:
            error_code = "E8002"  # Missing key in dictionary
        elif "AttributeError" in error_type:
            error_code = "E8003"  # Object attribute error
        elif "TypeError" in error_type:
            error_code = "E8004"  # Type mismatch
        
        # Return a JSON response with detailed error info
        return jsonify({
            "error": f"{error_code}: Server error - {error_type}",
            "message": error_msg,
            "type": error_type,
            "trace": error_traceback.split("\n")[-3:] if error_traceback else "No traceback"
        }), 500

# Add a health check endpoint for debugging
@app.route('/api/health', methods=['GET', 'OPTIONS'])
def health_check():
    if request.method == 'OPTIONS':
        # Handle preflight request
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
        return response
        
    # Display detailed environment info
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    
    # Check if we can access environment variables
    has_api_key = bool(os.getenv("ANTHROPIC_API_KEY"))
    
    # Report Flask and environment details
    return jsonify({
        "status": "ok",
        "timestamp": str(datetime.datetime.now()),
        "environment": os.environ.get('FLASK_ENV', 'development'),
        "python_version": python_version,
        "has_api_key": has_api_key,
        "server_time": time.time()
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)