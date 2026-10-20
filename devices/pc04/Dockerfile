# Dockerfile for PC-04 simulated monitoring device
# -------------------------------------------------------
FROM python:3.12-slim

WORKDIR /app

# Install required packages
RUN pip install --no-cache-dir psutil requests

# Copy PC-04 simulation script
COPY simulated_device_pc04.py .

# Run the monitoring agent
CMD ["python", "simulated_device_pc04.py"]
