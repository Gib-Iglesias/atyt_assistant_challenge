FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Usuario sin privilegios con UID fijo. /data se crea aqui y con este dueno,
# de modo que el volumen nombrado herede la propiedad al crearse por primera
# vez. El servicio api usa el mismo UID para poder escribir en el mismo volumen.
RUN useradd --uid 1000 --create-home app \
 && mkdir -p /data/media /app/staticfiles \
 && chown -R app:app /data /app \
 && chmod +x /app/entrypoint.sh

USER app

EXPOSE 8000
ENTRYPOINT ["/app/entrypoint.sh"]
