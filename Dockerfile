FROM python:3.12-slim

# Install git (required for the tool to check git config)
RUN apt-get update && \
    apt-get install -y --no-install-recommends git=1:2.47.3-0+deb13u1 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY tests/ ./tests/

# Install the package in development mode
RUN pip install --no-cache-dir -e ".[dev]"

# Create a test user and basic git config
RUN useradd -m testuser && \
    su - testuser -c "git config --global user.name 'Test User'" && \
    su - testuser -c "git config --global user.email 'test@example.com'"

USER testuser
WORKDIR /home/testuser

# Default command
CMD ["bash"]
