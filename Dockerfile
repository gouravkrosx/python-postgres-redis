# Dockerfile

FROM python:3.11-slim

# Accept the build argument APP_PATH
ARG APP_PATH
ENV APP_PATH=${APP_PATH} 

# Set the working directory to the provided APP_PATH
WORKDIR ${APP_PATH}

# Copy everything from the provided path on the host
COPY . ${APP_PATH}

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080

# Run the application with coverage, using APP_PATH
CMD ["python3", "-m", "coverage", "run", "-p", "app.py"]