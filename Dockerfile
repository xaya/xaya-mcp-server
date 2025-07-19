# Use the official Python slim image as a parent image
FROM python:3-slim

# Set the working directory in the container
WORKDIR /usr/src

# Copy the requirements files into the container
COPY requirements.txt ./

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the source folders as needed
COPY abi ./abi/
COPY app ./app/

# Create a non-root user
RUN useradd -ms /bin/bash python

# Switch to the non-root user
USER python

# Specify the entrypoint for the container
ENTRYPOINT ["python", "app/main.py"]
