FROM python:3.11-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8000 SUMO_HOME=/usr/share/sumo DS_MAX_QUEUED=1 DS_MAX_DURATION_MINUTES=15 DS_MEMORY_GUARD_RATIO=0.83 MALLOC_ARENA_MAX=2
RUN apt-get update && apt-get install -y --no-install-recommends sumo sumo-tools && rm -rf /var/lib/apt/lists/*
WORKDIR /srv/dynamicspeed
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN mkdir -p app
COPY main.py simulation.py __init__.py ./app/
COPY simulator.html ./simulator.html
COPY index.html ./index.html
EXPOSE 8000
CMD ["sh","-c","uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
