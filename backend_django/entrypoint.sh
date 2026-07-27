#!/bin/sh
# Orquesta el arranque del servicio fuente de verdad:
#   migrar -> estaticos -> sembrar -> indexar -> marcar listo
# El fichero /data/.ready es lo que libera el arranque del servicio api.
# Escrito en sh POSIX y arrancado con 'sh entrypoint.sh' para no depender del
# bit de permiso de ejecucion.
set -eu

READY_FLAG=/data/.ready
rm -f "$READY_FLAG"

echo "[django] aplicando migraciones..."
python manage.py migrate --noinput

echo "[django] recolectando estaticos..."
python manage.py collectstatic --noinput --clear >/dev/null

echo "[django] sembrando datos de ejemplo (perfil: ${SEED_PROFILE:-full})..."
python manage.py seed_demo

echo "[django] indexando documentos..."
python manage.py ingest_docs

touch "$READY_FLAG"
echo "[django] atyt-assistant listo -> admin en http://localhost:8000/admin"

exec python manage.py runserver 0.0.0.0:8000
