
# Use a Python base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements
COPY src/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create logs directory 
RUN mkdir -p /app/logs

# Copy app files
COPY src/ .

# Expose the port
EXPOSE 5000

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["python", "app.py"]
