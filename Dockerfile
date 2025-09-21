FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY tests/ ./tests/

# Install the package in development mode
RUN pip install --no-cache-dir -e ".[dev]"

# Create a test user and basic git config
RUN useradd -m testuser

USER testuser
WORKDIR /home/testuser

# Default command
CMD ["bash"]
