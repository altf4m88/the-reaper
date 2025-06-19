import os
import requests
from flask import request, jsonify
from .app import app

EVALUATOR_URL = os.getenv("EVALUATOR_URL", "http://localhost:8000")

@app.route('/api/subject/<uuid:subject_id>/evaluate', methods=['POST'])
def trigger_subject_evaluation(subject_id):
    """
    Forwards the evaluation request to the backend FastAPI service for a single subject.
    """
    try:
        url = f"{EVALUATOR_URL}/evaluate/subject/{subject_id}"
        resp = requests.post(url, headers={"accept": "application/json"})
        return (resp.text, resp.status_code, resp.headers.items())
    except Exception as e:
        return jsonify({"error": str(e)}), 500
