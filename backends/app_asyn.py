import json
import openai
import os
import flask
from flask_cors import CORS
from datetime import datetime
from flask import request, jsonify
import pandas as pd
import re
import asyncio
from asgiref.sync import async_to_sync
from async_chat import asy_chat_in
from async_database import asy_write_to_db
from dotenv import load_dotenv

load_dotenv()  # This loads the variables from .env

# Initialize Flask app
app = flask.Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Wrapper function to handle async functions in Flask
def async_route(route_function):
    def wrapper(*args, **kwargs):
        return async_to_sync(route_function)(*args, **kwargs)
    wrapper.__name__ = route_function.__name__
    return wrapper

@app.route('/async_chat', methods=['POST'])
@async_route
async def async_handle_chat():
    print("Async chat received")
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 415
    
    data = request.get_json()
    
    # Check if required field exists
    if 'input_text' not in data:
        return jsonify({"error": "input_text is required"}), 400
    
    # Extract fields from JSON
    input_text = data['input_text']
    system_prompt = data.get('system_prompt', "You are a helpful assistant")  # Optional
    model = data.get('model', 'gpt-4o-mini')  # Optional with default
    interaction_id = data.get('interaction_id')  # Optional
    chatbot_name = data.get('chatbot_name')  # Optional
    
    try:
        response = await asy_chat_in(
            input_text=input_text,
            system_prompt=system_prompt,
            model=model)
        
        interaction_date = datetime.now()
        await asy_write_to_db(
            texts=[input_text, response],
            interaction_id=interaction_id,
            chatbot_name=chatbot_name,
            interaction_date=interaction_date)
        
        # Added response to return value
        return jsonify({"response": response, "status": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/generate-leaderboard', methods=['GET'])
def generate_leaderboard():
    # Path to your Excel file
    submission_dir = os.path.join(os.path.dirname(__file__), 'submission')
    if not os.path.exists(submission_dir):
        return jsonify({"status": "success", "message": "No submissions found"}), 200
    
    # Get all submission files
    submission_files = [f for f in os.listdir(submission_dir) if f.endswith('.json')]
    
    # Read all submission files
    submissions = []
    for file in submission_files:
        with open(os.path.join(submission_dir, file), 'r') as f:
            submissions.append(json.load(f))
    
    # Write to the csv
    path = os.path.join(os.path.dirname(__file__), 'data', 'leaderboard.csv')
    pd.DataFrame(submissions).to_csv(path, index=False)
    
    return jsonify({"status": "success", "message": "Leaderboard generated successfully"}), 200

@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    try:
        # Generate leaderboard
        response = generate_leaderboard()
        
        # Path to your Excel file
        excel_path = os.path.join(os.path.dirname(__file__), 'data', 'leaderboard.csv')
        
        # Check if file exists
        if not os.path.exists(excel_path):
            # Return sample data if file doesn't exist
            leaderboard_data = [
                {"name": "Team 1", "score": 100},
                {"name": "Team 2", "score": 90},
                {"name": "Team 3", "score": 80}
            ]
            return jsonify(leaderboard_data)
        
        # Read Excel file
        df = pd.read_csv(excel_path)
        
        # Sort by score descending
        df = df.sort_values(by='score', ascending=False)
        
        # Convert to list of dictionaries (JSON format)
        leaderboard_data = df.to_dict('records')
        
        return jsonify(leaderboard_data)
    except Exception as e:
        print(f"Leaderboard error: {e}")
        return jsonify({"error": str(e)}), 500

from evaluate_submission import calculate_accuracy

@app.route('/api/evaluate-songs', methods=['POST'])
def evaluate_songs():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 415
    
    data = request.get_json()
    
    # Check for required fields
    if 'team_name' not in data or 'user_text' not in data:
        return jsonify({"error": "team_name and user_text are required"}), 400
    
    team_name = data['team_name']
    user_text = data['user_text']
    
    # Call the evaluation function
    result = calculate_accuracy(team_name, user_text)
    
    if result.get("status") == "error":
        return jsonify(result), 500
    
    # Write the results to submission folder 
    submission_dir = os.path.join(os.path.dirname(__file__), 'submission')
    if not os.path.exists(submission_dir):
        os.makedirs(submission_dir)
    
    path = team_name + "_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".json"
    with open(os.path.join(submission_dir, path), 'w') as f:
        json.dump(result, f)
    
    # Update the leaderboard
    score = result.get("score")
    score = float(score)*100
    last_updated = result.get("last_updated")
    
    return jsonify({"status": "success", "message": "Submission saved successfully", "score": score, "last_updated": last_updated}), 200

# Create a handshake endpoint to check if the backend is running
@app.route('/api/hi', methods=['GET', 'POST', 'PUT', 'DELETE'])
def handshake():
    return jsonify({"status": "success", "message": "Backend is running"}), 200

if __name__ == '__main__':
    # You can run with ASGI server for better async support
    import uvicorn
    from asgiref.wsgi import WsgiToAsgi
    
    # Convert WSGI app to ASGI
    asgi_app = WsgiToAsgi(app)
    
    # Run with uvicorn
    uvicorn.run(asgi_app, host="0.0.0.0", port=5000)
    
    # Alternatively, use the original Flask way:
    # app.run(debug=True)