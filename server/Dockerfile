FROM python:3.10-bullseye

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip3 install -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose the FastAPI port
EXPOSE 7860

# Run the FastAPI server
CMD ["python3", "server.py"] 