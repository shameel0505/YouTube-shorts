FROM python:3.11-slim

WORKDIR /app

# Only install the dependencies needed for the ping test
RUN pip install notebooklm-py requests

COPY experiments/test_gcp_auth.py .
# We copy the JSON file directly into the image so we don't have to deal with escaping variables
COPY experiments/gcp_storage_state.json .

CMD ["python", "test_gcp_auth.py"]
