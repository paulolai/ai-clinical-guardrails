FROM nvidia/cuda:12.1-devel-ubuntu22.04

WORKDIR /app

# Install Python and dependencies
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy service code
COPY . .

# NOTE: Model is NOT downloaded here (keeps image small).
# Model downloads at runtime via volume mount to /root/.cache/huggingface
# See docker-compose.yml for volume configuration

EXPOSE 8003

CMD ["python3", "llm_service.py"]
