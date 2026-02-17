FROM python:3.12-slim

WORKDIR /

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app /app

EXPOSE 9000

CMD ["fastmcp", "run", "app/server.py:mcp", "--host", "0.0.0.0", "--transport", "http", "--port", "9000"]