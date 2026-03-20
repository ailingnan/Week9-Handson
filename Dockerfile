# Use official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory to /app
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . .

# Make scripts executable
RUN chmod +x scripts/run.sh scripts/run_ingestion.sh

# Expose Streamlit port
EXPOSE 8501

# Define environment variable
ENV PYTHONPATH=/app

# Run scripts/run.sh when the container launches
CMD ["streamlit", "run", "app/streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
