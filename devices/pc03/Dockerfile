# Dockerfile for PC-03 simulated monitoring device
# -------------------------------------------------------
FROM python:3.12-slim

WORKDIR /app

# Install required packages
RUN pip install --no-cache-dir psutil requests

# Copy PC-03 simulation script
COPY simulated_device_pc03.py .

# Run the monitoring agent
CMD ["python", "simulated_device_pc03.py"]
