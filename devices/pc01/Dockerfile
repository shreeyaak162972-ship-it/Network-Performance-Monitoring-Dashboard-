# Dockerfile for PC-01 simulated monitoring device
# -------------------------------------------------------
# Uses the same base image as the main web service so
# we don't need to pull an additional image.

FROM python:3.12-slim

# Working directory inside the container
WORKDIR /app

# Install only the libraries this agent needs
# (psutil is listed here even though we use simulated values;
#  it will be needed later when real metrics are collected)
RUN pip install --no-cache-dir psutil requests

# Copy only the simulated device script into the container
COPY simulated_device.py .

# Run the monitoring agent when the container starts
CMD ["python", "simulated_device.py"]
