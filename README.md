# att_assistant_challenge

Asistente de chat interno para equipos de soporte. Responde preguntas sobre la
documentación de producto **citando la fuente exacta** (documento y página),
consulta datos del sistema (estado de un pedido, historial de un cliente) y
**escala un ticket** cuando no puede resolver con la información disponible.

Multi-tenant, con streaming token a token y sin ninguna dependencia de
infraestructura externa.

---

## Arranque

Requisitos: **Docker y Docker Compose. Nada más. Sin API key.**

```bash
git clone https://github.com/Gib-Iglesias/att_assistant_challenge.git
cd atyt_assistant_challenge
cp .env.example .env
docker compose up --build
```

Ese es el comando. El `.env.example` ya trae valores que funcionan tal cual: el
proveedor de LLM por defecto es una implementación falsa que no necesita red ni
credenciales.

El primer arranque construye las imágenes (unos minutos, según la red), aplica
migraciones, genera los datos de ejemplo —incluidos los PDF sintéticos, con uno
de 400 páginas— y los indexa. **La siembra y la indexación tardan menos de un
minuto**; lo que domina el primer arranque es la construcción de las imágenes.
Los siguientes arranques son inmediatos: el volumen persiste y el seed es
idempotente.

Volumen que se genera: 40 tenants, ~4.000 pedidos, ~470 tickets, 122 documentos
(1.240 páginas) y unos 7.300 fragmentos indexados.

Cuando termine, en los logs aparece `atyt-assistant listo`.

| Servicio | URL | Para qué |
|---|---|---|
| Aplicación | http://localhost:8080 | El chat |
| Admin de Django | http://localhost:8000/admin | Datos, documentos, chunks marcados |
| API de IA | http://localhost:8001/docs | Swagger, generado automáticamente |

### Usuarios de ejemplo

Se crean en el seed. **Son credenciales de desarrollo**, no usar fuera de local.

| Usuario | Contraseña | Rol |
|---|---|---|
| `admin` | `admin123` | Superusuario, sin tenant |
| `agente_acme` | `demo1234` | Agente de soporte, tenant `acme` |
| `agente_globex` | `demo1234` | Agente de soporte, tenant `globex` |

Entra con `agente_acme` y pregunta *"¿cuánto tardan los reembolsos?"* o
*"¿en qué estado está el pedido ACME-001042?"*.

---

## Elegir el modelo de LLM

Todo el acceso al proveedor vive detrás de una interfaz. Cambiar de modelo son
dos variables en `.env`, sin tocar código:

```bash
LLM_PROVIDER=fake          # fake | openai | anthropic | gemini | ollama
LLM_MODEL=                 # p. ej. gpt-4o-mini, claude-sonnet-4-5, llama3.1
LLM_API_KEY=               # la key del proveedor elegido
LLM_BASE_URL=              # opcional: ollama o gateways compatibles
LLM_MAX_CONCURRENCY=20     # límite global de la cuenta
LLM_MAX_CONTEXT_TOKENS=6000
```

`fake` es el valor por defecto y el que permite arrancar y correr los tests sin
red. Emite token a token con la misma interfaz que el proveedor real, así que
el frontend no distingue uno de otro.

Si eliges un proveedor real y falta `LLM_API_KEY`, el servicio **falla al
arrancar con un mensaje explícito** en lugar de degradarse en silencio.

---

## Tests

```bash
docker compose run --rm api pytest -q
docker compose run --rm django python manage.py test
```

Corren sin red y sin API key. Incluyen el test de aislamiento entre tenants
descrito en `DECISIONES.md`.

---

## Comandos útiles

```bash
docker compose down -v                                   # borrar todo y empezar limpio
docker compose exec django python manage.py seed_demo    # regenerar datos
docker compose exec django python manage.py ingest_docs  # reindexar documentos
docker compose logs -f api                               # ver el servicio de IA
```

Para iterar rápido, `SEED_PROFILE=fast` en `.env` genera el mismo volumen de
pedidos pero documentos cortos, y baja el arranque a menos de 30 segundos.

---

