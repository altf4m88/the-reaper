import os
import uuid
from flask import Flask, render_template, abort, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Uuid, Float, Integer, Text, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship, joinedload
from dotenv import load_dotenv
import requests

# --- App and Database Configuration ---

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

INPUT_PRICE_PER_MILLION_TOKENS = 0.075  # Price for 1M input tokens in USD
OUTPUT_PRICE_PER_MILLION_TOKENS = 0.30  # Price for 1M output tokens in USD


# --- Database Models (copied from your existing schema) ---

class Subject(db.Model):
    __tablename__ = 'subjects'
    id = db.Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject_name = db.Column(String(255), nullable=False, unique=True)
    questions = relationship("Question", back_populates="subject")
    # Add relationship to task_answers for easy querying
    task_answers = relationship("TaskAnswer", back_populates="subject")

class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(String(255), nullable=False)
    task_answers = relationship("TaskAnswer", back_populates="student")

class Question(db.Model):
    __tablename__ = 'questions'
    id = db.Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject_id = db.Column(Uuid(as_uuid=True), ForeignKey('subjects.id'), nullable=False)
    question_text = db.Column(Text, nullable=False)
    preferred_answer = db.Column(Text)
    subject = relationship("Subject", back_populates="questions")
    task_answers = relationship("TaskAnswer", back_populates="question")
    request_logs = relationship("RequestLog", back_populates="question")

class TaskAnswer(db.Model):
    __tablename__ = 'task_answers'
    id = db.Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Add subject_id for direct relationship and easier querying
    subject_id = db.Column(Uuid(as_uuid=True), ForeignKey('subjects.id'), nullable=False)
    question_id = db.Column(Uuid(as_uuid=True), ForeignKey('questions.id'), nullable=False)
    student_id = db.Column(Uuid(as_uuid=True), ForeignKey('students.id'), nullable=False)
    answer = db.Column(Text, nullable=False)
    status = db.Column(Boolean, nullable=True)
    ground_truth = db.Column(Boolean, nullable=True) # Assuming ground_truth exists per ERD
    
    # Relationships
    subject = relationship("Subject", back_populates="task_answers")
    question = relationship("Question", back_populates="task_answers")
    student = relationship("Student", back_populates="task_answers")

class RequestLog(db.Model):
    __tablename__ = 'request_logs'
    id = db.Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_time = db.Column(Float, nullable=False)
    question_count = db.Column(Integer, nullable=False)
    prompt_token_count = db.Column(Integer, nullable=False)
    candidates_token_count = db.Column(Integer, nullable=False)
    total_token_count = db.Column(Integer, nullable=False)
    question_id = db.Column(Uuid(as_uuid=True), ForeignKey('questions.id'), nullable=False)
    question = relationship("Question", back_populates="request_logs")


# --- Flask Routes ---

@app.route('/')
def index():
    """
    Dashboard route. Fetches all subjects from the database
    and displays them on the main page.
    """
    try:
        subjects = db.session.execute(db.select(Subject).order_by(Subject.subject_name)).scalars().all()
        return render_template('index.html', subjects=subjects)
    except Exception as e:
        # Handle potential database connection errors gracefully
        print(f"Error fetching subjects: {e}")
        abort(500, description="Could not connect to the database to fetch subjects.")


@app.route('/subject/<uuid:subject_id>')
def subject_detail(subject_id):
    """
    Subject detail route. Fetches a specific subject, all its related
    questions/answers, and calculates the LLM's evaluation accuracy.
    """
    try:
        subject = db.session.get(Subject, subject_id)
        if not subject:
            abort(404, description="Subject not found.")

        # --- Accuracy Calculation ---
        # 1. Count total answers that have been evaluated by the LLM (status is not null)
        total_evaluated = db.session.execute(
            db.select(db.func.count(TaskAnswer.id))
            .where(TaskAnswer.subject_id == subject_id)
            .where(TaskAnswer.status.isnot(None))
        ).scalar_one()

        # 2. Count answers where the LLM's evaluation matches the ground_truth
        correctly_evaluated = db.session.execute(
            db.select(db.func.count(TaskAnswer.id))
            .where(TaskAnswer.subject_id == subject_id)
            .where(TaskAnswer.status == TaskAnswer.ground_truth)
        ).scalar_one()

        # 3. Calculate percentage
        accuracy = (correctly_evaluated / total_evaluated) * 100 if total_evaluated > 0 else None

        # --- Data Fetching for Display ---
        # Eagerly load data to prevent N+1 query problem.
        questions = db.session.execute(
            db.select(Question)
            .where(Question.subject_id == subject_id)
            .options(
                joinedload(Question.task_answers).joinedload(TaskAnswer.student)
            )
        ).scalars().unique().all()

        return render_template('subject_detail.html', subject=subject, questions=questions, accuracy=accuracy)
    except Exception as e:
        print(f"Error fetching subject details: {e}")
        abort(500, description="Could not fetch subject details.")

@app.route('/logs')
def request_logs():
    """
    Renders a page with an aggregated summary of request logs,
    including token usage and estimated costs.
    """
    try:
        # Build the aggregation query for the per-subject breakdown
        log_summary_query = db.session.query(
            Subject.subject_name.label('subject_name'),
            db.func.sum(RequestLog.request_time).label('total_request_time'),
            db.func.sum(RequestLog.total_token_count).label('total_tokens'),
            db.func.sum(RequestLog.prompt_token_count).label('prompt_tokens'),
            db.func.sum(RequestLog.candidates_token_count).label('candidates_tokens'),
            db.func.count(RequestLog.id).label('request_count')
        ).select_from(RequestLog).join(RequestLog.question).join(Question.subject).group_by(Subject.subject_name)

        log_summary = log_summary_query.all()

        # Process results for the table and calculate grand totals
        processed_summary = []
        grand_total_tokens = 0
        grand_total_cost = 0.0
        grand_total_time = 0.0

        for row in log_summary:
            input_cost = (row.prompt_tokens / 1_000_000) * INPUT_PRICE_PER_MILLION_TOKENS
            output_cost = (row.candidates_tokens / 1_000_000) * OUTPUT_PRICE_PER_MILLION_TOKENS
            total_cost = input_cost + output_cost
            processed_summary.append({
                'name': row.subject_name,
                'time': row.total_request_time,
                'total_tokens': row.total_tokens,
                'input_cost': input_cost,
                'output_cost': output_cost,
                'total_cost': total_cost,
                'request_count': row.request_count
            })
            # Aggregate grand totals
            grand_total_tokens += row.total_tokens
            grand_total_cost += total_cost
            grand_total_time += row.total_request_time

        # Calculate overall averages
        total_request_count = db.session.query(db.func.count(RequestLog.id)).scalar()
        average_inference_time = grand_total_time / total_request_count if total_request_count > 0 else 0

        return render_template(
            'request_logs.html',
            summary=processed_summary,
            grand_total_tokens=grand_total_tokens,
            grand_total_cost=grand_total_cost,
            average_inference_time=average_inference_time
        )
    except Exception as e:
        print(f"Error fetching request logs: {e}")
        abort(500, description="Could not fetch request log summary.")

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


if __name__ == '__main__':
    app.run(debug=True)
