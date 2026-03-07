# Dockerfile for User Service
# Using Python 3.9 Alpine for minimal image size and security
FROM python:3.9-alpine

# Security: Create non-root user for running the application
RUN addgroup -g 1001 appgroup && \
    adduser -D -u 1001 -G appgroup appuser

# Set working directory
WORKDIR /app

# Install system dependencies
# Security: Update packages and install only necessary dependencies
RUN apk update && \
    apk upgrade && \
    apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    curl

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
# Security: Install without cache to reduce image size
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .

# Change ownership to non-root user
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose port 5001
EXPOSE 5001

# Health check for container monitoring
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5001/health || exit 1

# Run the application
# Security: Use gunicorn for production deployment
CMD ["python", "app.py"]