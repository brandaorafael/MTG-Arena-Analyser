FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Set PYTHONPATH so Python can find the src module
ENV PYTHONPATH=/app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
