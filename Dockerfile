# Start with a slightly newer, more stable Python image (Debian Bullseye is Python 3.9's current stable base)
FROM python:3.9.18-slim-bullseye

# Set environment variable globally for non-interactive installs
ENV DEBIAN_FRONTEND=noninteractive

# Install System Dependencies in a single, robust layer
# build-essential is added to fix the pyaesni compilation error.
RUN apt update -y && apt install -y --no-install-recommends git wget pv jq python3-dev ffmpeg mediainfo neofetch build-essential && rm -rf /var/lib/apt/lists/*

# Create working directory and set permissions (best practice)
WORKDIR /bot
RUN chmod 777 /bot

# Ensure Python build tools are up-to-date BEFORE installing requirements
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy application files
COPY . .

# Install Python requirements
RUN pip3 install -r requirements.txt

# Final command to run the application
CMD ["bash","run.sh"]

