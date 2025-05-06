# Use official Python image
FROM python:3.11

# Install PostgreSQL client tools (for pg_isready)
RUN apt-get update && apt-get install -y postgresql-client

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy wait-for script and make it executable
COPY wait_for_postgres.sh /wait_for_postgres.sh
RUN chmod +x /wait_for_postgres.sh

# Run the wait-for script on startup
CMD ["sh", "-c", "/wait_for_postgres.sh && python app.py"]

