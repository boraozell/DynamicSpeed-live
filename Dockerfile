FROM python:3.11-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8000
RUN apt-get update && apt-get install -y --no-install-recommends sumo sumo-tools && rm -rf /var/lib/apt/lists/*
WORKDIR /srv/dynamicspeed
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py simulation.py __init__.py ./app/
COPY index.html ./index.html
COPY simulator.html ./simulator.html
EXPOSE 8000
CMD ["sh","-c","uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
