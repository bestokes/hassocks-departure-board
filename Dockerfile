# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libnspr4 \
    libnss3 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    xdg-utils \
    libxss1 \
    libxcb1 \
    libxkbcommon0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and browsers
RUN pip install playwright
RUN playwright install chromium
RUN playwright install-deps

# Copy only the required files
COPY app.py .
COPY screenshot_service.py .
COPY requirements.txt .
COPY templates/ templates/
COPY static/ static/

# Make port 5001 available to the world outside this container
EXPOSE 5001

# Define environment variable for Flask
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Run app.py when the container launches
CMD ["python", "app.py"]
