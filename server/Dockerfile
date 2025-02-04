FROM python:3.11-bullseye

WORKDIR /app

# Upgrade pip and install Python dependencies from requirements.txt,
# along with the pipecat-ai and pipecat-ai-flows packages from PyPI.
COPY server/requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install pipecat-ai[daily,openai,deepgram,cartesia,silero] && \
    pip install pipecat-ai-flows

# Copy the rest of the application code into the container.
COPY . /app

# Expose the FastAPI server port.
EXPOSE 7860

# Run the FastAPI server with the "flow" bot type.
CMD ["python3", "server/main.py", "--bot-type", "flow"] 