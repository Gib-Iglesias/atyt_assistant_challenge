FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

# El paquete se importa como service_ai.*, asi que se copia dentro de ese subdir.
COPY . /app/service_ai/

# Mismo UID que el contenedor django, para compartir el volumen /data.
RUN useradd --uid 1000 --create-home app \
 && chmod +x /app/service_ai/entrypoint.sh \
 && chown -R app:app /app
USER app

EXPOSE 8001
CMD ["sh", "/app/service_ai/entrypoint.sh"]
