FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# The asterisk makes this optional so the build never fails
COPY real_policies.json* ./

# Copy the rest of your environment files
COPY . .

ENV PYTHONUNBUFFERED=1
ENV MAX_CONCURRENT_ENVS=100
ENV PORT=7860
ENV HOST=0.0.0.0

EXPOSE 7860

# Reverted to point to the server directory per your constraints
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
