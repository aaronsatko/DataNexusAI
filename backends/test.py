# Request to the backend
import logging
import requests
import json

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('backend_tests.log')
    ]
)
logger = logging.getLogger(__name__)

path = "http://127.0.0.1:5000"

# Test the handshake endpoint
def test_handshake():
    logger.info("Testing handshake endpoint")
    try:
        response = requests.get(path + "/api/hi")
        logger.info(f"Handshake response: {response.json()}")
        return response.json()
    except Exception as e:
        logger.error(f"Handshake test failed: {str(e)}")
        return {"status": "error", "message": str(e)}


# Test the evaluation endpoint
def test_evaluation():
    logger.info("Testing evaluation endpoint")
    try:
        response = requests.post(path + "/api/evaluate-songs", json={"team_name": "test_team", "user_text": "Classify the music genre in the best way"})
        logger.info(f"Evaluation response: {response.json()}")
        return response.json()
    except Exception as e:
        logger.error(f"Evaluation test failed: {str(e)}")
        return {"status": "error", "message": str(e)}

# Main function to run tests
def run_tests():
    handshake_result = test_handshake()
    if handshake_result.get("status") == "success":
        evaluation_result = test_evaluation()
        return evaluation_result
    return handshake_result

if __name__ == "__main__":
    result = run_tests()
    print(json.dumps(result, indent=2))
