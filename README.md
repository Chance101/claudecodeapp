# Customer Service Chatbot

A customer service chatbot built with Flask and the Claude API.

## Features

- Web-based chat interface
- Conversation memory
- Responsive design
- Typing indicators
- Multiple conversation support

## Setup

1. Clone the repository
2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Set up your .env file with your Anthropic API key:
   ```
   ANTHROPIC_API_KEY=your_api_key_here
   ```
5. Start the application:
   ```
   python app.py
   ```

## Usage

1. Open your browser and go to http://localhost:8080/
2. Type your message in the input field and press Enter or click Send
3. Wait for the chatbot to respond

## Deployment

This app is configured for deployment on Vercel using the included `vercel.json` configuration file.

## Customizing the Chatbot

You can customize the behavior of the chatbot by modifying the system prompt in the `app.py` file. The system prompt defines how the chatbot will behave and what capabilities it has.

## Project Structure

- `app.py`: Main Flask application
- `templates/index.html`: Frontend chat interface
- `.env`: Environment variables (API key)
- `.env.example`: Example environment file
- `requirements.txt`: Python dependencies
- `vercel.json`: Vercel deployment configuration