# README: RAG + SSE Demo

## Overview
This is a **Streamlit**-based web application that demonstrates the integration of **Retrieval-Augmented Generation (RAG)** with **Server-Sent Events (SSE)**. The app allows users to send queries to a backend and receive streaming responses containing a **RAG-generated prompt** and relevant **source documents**.

## Features
- **Streamlit UI** for entering queries and receiving responses.
- **Server-Sent Events (SSE)** for real-time retrieval of data.
- **Logging & Debugging** for tracking application flow.
- **Environment variable support** via `.env` files.
- **Session state management** to store retrieved data.

## Installation

### Prerequisites
- **Python 3.8+**
- **pip** installed

### Setup
1. **Clone the repository**:
   git clone <repository_url>
   cd <repository_name>

2. **Create and activate a virtual environment**:
   
   python -m venv venv
   source venv/bin/activate  # On macOS/Linux
   venv\Scripts\activate  # On Windows

3. **Install dependencies**:
   pip install -r requirements.txt

4. **Set up environment variables** (Optional):
   - Create a `.env` file in the project root.
   - Add relevant variables if needed.

## Usage

### Run the Streamlit App
streamlit run frontend_demo.py


### Interacting with the App
1. **Enter a query** in the text box.
2. **Provide an optional user group token**.
3. **Click "Send Query"** to retrieve RAG-generated results via SSE.
4. **View the retrieved RAG prompt and sources**.
5. **Click "Reset"** to clear the session state.

## Configuration

### Environment Variables
This app uses `dotenv` to load environment variables. Ensure you have a `.env` file if required.

### SSE Endpoint
By default, the app connects to:
- `http://127.0.0.1:4096/retrieve_chunks`
- This can be modified in the script as needed.