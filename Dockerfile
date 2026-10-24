FROM python:3.9-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080

WORKDIR /app
COPY requirements.txt ./
RUN python -m pip install --upgrade pip wheel \
    && python -m pip install setuptools==70.3.0 \
    && python -m pip install -r requirements.txt

COPY service ./service
RUN chgrp -R 0 /app && chmod -R g=u /app
USER 1001
EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--access-logfile", "-", "--error-logfile", "-", "service:app"]
