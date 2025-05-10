# Use the official Python 3.11 slim image as the base image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install build tools and necessary libraries
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file to the container
COPY requirements.txt .

# Install Python dependencies (including Hypercorn)
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire contents of this folder into a subdirectory named "rag_retriever_service"
# This ensures that the package "rag_retriever_service" exists in /app.
COPY . ./rag_retriever_service

# Expose port 4096 for Hypercorn
EXPOSE 4096

# Run the FastAPI application with Hypercorn on port 4096.
# The module is referenced using its full absolute package name.
CMD ["hypercorn", "rag_retriever_service.src.core.app:app", "--bind", "0.0.0.0:4096"]