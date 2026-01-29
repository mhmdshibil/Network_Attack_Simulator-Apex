# Network Attack Simulator-Apex

This project is a network attack simulator with a backend API for detecting and analyzing network attacks. It uses a machine learning model to classify network traffic and provides a set of APIs to interact with the system.

## Key Features

*   **Attack Simulation**: Scripts to generate synthetic normal and attack traffic (e.g., port scans).
*   **Attack Detection**: A machine learning model to detect attacks from network traffic.
*   **Analytics API**: Endpoints to get insights into attack trends, top attackers, and more.
*   **Response Engine**: An automated response engine to take actions based on detected risks.
*   **FastAPI Backend**: A modern, fast (high-performance) web framework for building APIs.

## Project Structure

The project is organized into the following main directories:

*   `backend/`: The FastAPI application.
    *   `app/`: The core application logic.
        *   `api/`: API route definitions.
        *   `analytics/`: Modules for data analysis, risk assessment, and correlation.
        *   `core/`: Core application settings and path configurations.
        *   `ml/`: Machine learning models, training scripts, and utilities.
        *   `response/`: The automated response engine.
        *   `schemas/`: Pydantic schemas for data validation.
        *   `services/`: Services for detection and log processing.
*   `data/`: Raw and processed data.
*   `models/`: Trained machine learning models.
*   `scripts/`: Scripts for generating data.

## Getting Started

### Prerequisites

*   Python 3.8+
*   pip

### Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/your-username/Network_Attack_Simulator-Apex.git
    cd Network_Attack_Simulator-Apex
    ```

2.  Install the required packages:
    ```bash
    pip install -r requirements.txt
    pip install -r backend/requirements.txt
    ```

### Running the Application

1.  Generate some sample data:
    ```bash
    python scripts/generate_normal_traffic.py
    python scripts/generate_port_scan_attack.py
    ```

2.  Train the machine learning model:
    ```bash
    python backend/app/ml/train_model.py
    ```

3.  Run the FastAPI application:
    ```bash
    uvicorn backend.app.main:app --reload
    ```

The API will be available at `http://127.0.0.1:8000`. You can access the API documentation at `http://127.0.0.1:8000/docs`.