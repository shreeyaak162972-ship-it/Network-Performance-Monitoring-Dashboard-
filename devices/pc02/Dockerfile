# Dockerfile for PC-02 simulated monitoring device
# -------------------------------------------------------
FROM python:3.12-slim

WORKDIR /app

# Install required packages
RUN pip install --no-cache-dir psutil requests

# Copy PC-02 simulation script
COPY simulated_device_pc02.py .

# Run the monitoring agent
CMD ["python", "simulated_device_pc02.py"]
