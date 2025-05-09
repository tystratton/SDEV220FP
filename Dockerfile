# Use official Python image
FROM python:3.11

# Install PostgreSQL client tools (for pg_isready)
RUN apt-get update && apt-get install -y postgresql-client

# Set working directory
WORKDIR /app

# Copy project files first (excluding .dockerignore items)
COPY . /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Make it executable from its location in /app
RUN chmod +x /app/wait_for_postgres.sh

# ---- START DEBUG ----
RUN ls -la /app/
# ---- END DEBUG ----

# Run the wait-for script on startup, referencing it with its full path
CMD ["sh", "-c", "/app/wait_for_postgres.sh && python app.py"]

