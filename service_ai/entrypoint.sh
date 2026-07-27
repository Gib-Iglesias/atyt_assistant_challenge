#!/bin/sh
# Un solo worker, a proposito: el limite de 20 peticiones concurrentes al
# proveedor se aplica con un semaforo en proceso, que deja de ser un limite real
# con varios workers. Ver docs/DECISIONES.md, seccion 4.
#
# Escrito en sh POSIX (no bash) y arrancado con 'sh entrypoint.sh' desde el
# Dockerfile, para que no dependa del bit de permiso de ejecucion del fichero,
# que puede perderse al descomprimir en algunos sistemas.
set -eu

echo "[api] esperando a que la base este lista..."
while [ ! -f /data/.ready ]; do
  sleep 1
done

echo "[api] arrancando FastAPI (Swagger en :8001/docs)"
exec uvicorn service_ai.main:app --host 0.0.0.0 --port 8001 --workers 1
