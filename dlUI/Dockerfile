# Base Image based on python-slim image
FROM python:3.7.5

RUN apt-get update
RUN apt-get install -y libgomp1 gcc

# Copying the content in the app directory. Ignoring the content in .dockerignore
COPY . /app

# Changing Working directory
WORKDIR /app

# Installing dependencies
RUN pip install --upgrade pip && \
    pip install -U cookiecutter

RUN pip install -r requirements.txt

RUN pip install -e dlweb
# Exposing ports
EXPOSE 8050

CMD run-dlweb-dev --host 0.0.0.0

 

