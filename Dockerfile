FROM python:3.11-slim

WORKDIR /app

# git is required at runtime: the agent shallow-clones the analyzed repo
# so it can run pytest/bandit against the ACTUAL code being reviewed.
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
