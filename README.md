
# AI Answer Evaluator Dashboard

This project is a Flask-based web application that provides a dashboard to display, evaluate, and analyze student answers for various subjects using an AI model. It calculates evaluation accuracy, tracks token usage, and estimates costs associated with the AI evaluation service.

## Features

* **Subject Dashboard**: View a list of all subjects from the database.
* **Detailed Subject View**: For each subject, view all questions, student-provided answers, the AI's evaluation, and the ground truth.
* **AI Evaluation**: Trigger an AI-powered evaluation for all answers of a specific subject.
* **Accuracy Calculation**: Automatically calculates the accuracy of the LLM's evaluation against the ground truth.
* **Request & Cost Logging**: A dedicated page to view aggregated statistics on API requests, including token counts, inference time, and estimated costs, broken down by subject.

## Prerequisites

Before you begin, ensure you have the following installed:

* Python 3.7+
* pip
* A running PostgreSQL instance

## Getting Started

Follow these instructions to get the project up and running on your local machine.

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd the-reaper
````

### 2\. Set Up and Activate the Virtual Environment

Using a virtual environment is highly recommended.

**For macOS and Linux users:**

```bash
python3 -m venv venv
source venv/bin/activate
```

**For Windows users:**

```bash
python -m venv venv
.\venv\Scripts\activate
```

After running the activation command, you should see `(venv)` at the beginning of your terminal prompt.

### 3\. Install Dependencies

With your virtual environment active, install the required packages:

```bash
pip install -r requirements.txt
```

### 4\. Configure Environment Variables

Create a new file named `.env` in the root of your project directory. Copy the following and replace the placeholder values with your actual database credentials.

```
# The connection string for your PostgreSQL database
DATABASE_URL="postgresql://<user>:<password>@<host>:<port>/<database_name>"

# The URL of the separate AI evaluator service
EVALUATOR_URL="http://localhost:8000"
```

### 5\. Running the Application

Once the setup is complete, run the Flask application:

```bash
python app.py
```

The application will start in debug mode and be accessible at **[suspicious link removed]**.

## How to Use

1.  Open your web browser and navigate to `http://127.0.0.1:5000`.
2.  The main dashboard will show a list of subjects.
3.  Click on a subject to view its details, including questions and student answers.
4.  On the subject detail page, click the **"Evaluate All Answers (AI)"** button to send the answers to the evaluation service.
5.  Navigate to the **"Request Logs"** page from the header to see a summary of API usage and costs.

<!-- end list -->
