FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir streamlit requests
CMD ["streamlit", "run", "dashboard.py", "--server.port=8080", "--server.address=0.0.0.0"]
