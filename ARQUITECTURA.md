# Arquitectura

## 1. Vista general

Tres contenedores y un volumen compartido. Ninguna pieza de infraestructura
adicional: sin Redis, sin motor de búsqueda, sin broker de colas.

```
                    ┌──────────────────────┐
                    │   web  (React+nginx) │   :8080
                    │   chat + proxy       │
                    └──────────┬───────────┘
                               │ SSE  /api/chat/stream
                    ┌──────────▼───────────┐
                    │   api  (FastAPI)     │   :8001
                    │   orquestador RAG    │
                    │   JWT → tenant fijo   │
                    └──┬────────┬───────┬──┘
                       │        │       │
          recuperación │        │ datos │ generación
                       │        │       │
        ┌──────────────▼─┐ ┌────▼─────┐ └──► LLMProvider
        │ FTS5 / BM25    │ │ Repos    │      (semáforo 20)
        │ chunks+páginas │ │ pedidos  │
        └──────────────┬─┘ └────┬─────┘
                       │        │
                    ┌──▼────────▼──────────┐
                    │  SQLite (WAL)        │  volumen /data
                    │  esquema: Django     │
                    └──────────▲───────────┘
                               │ migraciones, seed, ingesta
                    ┌──────────┴───────────┐
                    │  django              │   :8000
                    │  modelos + admin     │
                    └──────────────────────┘
```

### Reparto de responsabilidades

| Componente | Hace | No hace |
|---|---|---|
| `django` | Define el esquema, corre migraciones, admin, seed, ingesta de PDF | No atiende tráfico de chat |
| `api` | Autentica, recupera, orquesta, transmite, escala tickets | **Nunca migra el esquema** |
| `web` | Renderiza el chat, consume SSE, muestra citas | No habla con la base |

Un solo proceso escribe el esquema. Es lo que hace tolerable compartir un
fichero SQLite entre dos servicios.

---

## 2. Flujo de una consulta

1. **El agente envía la pregunta.** El frontend hace `POST /api/chat/stream`
   con el JWT en cabecera `Authorization`. No se usa `EventSource` nativo
   porque no admite cabeceras; se lee la respuesta con `fetch` +
   `ReadableStream` y se parsea SSE en el cliente.

2. **Autenticación y contexto de tenant.** FastAPI valida la firma del JWT con
   el secreto compartido y construye un `TenantContext(user_id, tenant_id,
   is_support_agent)`. A partir de aquí, `tenant_id` es inmutable durante toda
   la petición.

3. **Recuperación.** Se consulta el índice FTS5 con la pregunta, filtrando por
   `tenant_id` **en la cláusula SQL**, no en el prompt. Devuelve los `k`
   mejores chunks por BM25, cada uno con `document_id`, `page_start`,
   `page_end` y `is_suspicious`.

4. **Herramientas de datos.** Si la pregunta menciona una referencia de pedido
   o un correo de cliente, se resuelven con funciones que reciben el
   `TenantContext` por inyección. **Ninguna acepta `tenant_id` como
   parámetro.**

5. **Construcción del prompt.** Los chunks se envuelven en bloques delimitados
   marcados como datos no confiables. Los resultados de herramientas van en su
   propio bloque. El presupuesto de contexto se aplica aquí: si los chunks
   exceden `LLM_MAX_CONTEXT_TOKENS`, se truncan por orden de BM25.

6. **Generación con límite global.** La llamada al proveedor pasa por un
   `asyncio.Semaphore(LLM_MAX_CONCURRENCY)`. Si el semáforo está lleno, la
   petición espera en cola y el cliente recibe un evento `queued` con su
   posición, para que la interfaz no parezca colgada.

7. **Streaming.** Se emiten eventos SSE tipados en lugar de texto plano:

   | Evento | Contenido |
   |---|---|
   | `queued` | Posición en cola, si aplica |
   | `token` | Fragmento de texto |
   | `citations` | Lista de fuentes con documento y páginas |
   | `escalated` | ID del ticket creado |
   | `done` | Cierre limpio |
   | `error` | Motivo legible |

   Las citas viajan al final porque sólo pueden validarse contra los chunks
   realmente recuperados cuando el texto está completo.

8. **Escalado.** Se crea un `Ticket` cuando no hay chunks por encima del umbral
   de BM25, cuando el modelo declara explícitamente que no puede responder, o
   cuando el agente lo pide. El ticket queda en estado `escalated` con la
   conversación adjunta.

---

## 3. Modelo de datos

Los seis modelos del enunciado están tal cual, sin renombrar ni quitar campos.
Se añaden los que faltaban para que el sistema sea operable:

**Del enunciado** — `Tenant`, `User`, `Order`, `Ticket`, `Document`.

**Añadidos:**

| Modelo | Por qué |
|---|---|
| `DocumentChunk` | `Document` no tiene dónde guardar el texto indexable. Guarda `tenant`, `document`, `ordinal`, `text`, `page_start`, `page_end`, `is_suspicious`. |
| `Conversation` | El enunciado pide un asistente de chat pero no define dónde vive el hilo. |
| `Message` | Turnos de la conversación, con las citas asociadas a cada respuesta. |

**Campos añadidos a modelos existentes:**

- `Document.file` (ruta del PDF en el volumen), `Document.checksum`,
  `Document.ingest_status` — el modelo original sólo tenía `filename`, sin
  forma de saber si el fichero existe ni si ya se indexó.

El índice FTS5 es una tabla virtual `chunk_fts` de contenido externo sobre
`DocumentChunk`: no duplica el texto, sólo guarda el índice invertido. Vive en
la misma base, así que no es infraestructura aparte. **No se crea en una
migración a propósito**, porque las migraciones deben poder aplicarse sobre
Postgres o MySQL; se crea y reconstruye desde `core/ingestion/fts.py`. Al migrar
a Postgres se reemplaza por `tsvector` y `GIN`.

**La ingesta vive en Django, la recuperación en FastAPI.** Son dos imágenes
distintas y no pueden importarse entre sí: escribir el índice es una
responsabilidad del dueño del esquema, y leerlo es del servicio de IA.

---

## 4. Recuperación: por qué BM25 y no embeddings

El enunciado exige arrancar y correr los tests **sin red y sin API key**. Un
sistema de embeddings tiene dos salidas, y ninguna es buena aquí: llamar al
proveedor (rompe el requisito de arranque sin credenciales) o empaquetar un
modelo local (imagen de más de un giga, contra el criterio de que levante en
una máquina limpia).

FTS5 viene compilado en SQLite, no añade dependencias, y para documentación de
producto con vocabulario controlado — políticas, procedimientos, referencias —
BM25 rinde bien. El coste es que falla con sinónimos y paráfrasis: preguntar
*"¿me devuelven el dinero?"* no encuentra un documento que sólo dice
*"reembolso"*.

Mitigación dentro del alcance: normalización sin acentos (`unicode61
remove_diacritics 2`) y expansión de la consulta con un diccionario corto de
sinónimos del dominio. La búsqueda híbrida queda documentada en `NO_HICE.md`
como la primera mejora.

**Chunking:** ventanas de ~900 caracteres con 150 de solapamiento, cortando en
límites de párrafo y **sin cruzar páginas**, para que la cita apunte a una
página concreta y no a un rango difuso.

**Limpieza de encabezados:** la extracción descarta las líneas que se repiten
como cabecera en la mayoría de las páginas y los números de página sueltos. Sin
esto, el título del documento acaba dentro de cada fragmento y BM25 puntúa
igual de alto todas las páginas del mismo documento, que es justo lo contrario
de lo que necesita una cita útil.

---

## 5. Concurrencia

Dos límites distintos que suelen confundirse:

| Límite | Valor | Cómo se respeta |
|---|---|---|
| Usuarios concurrentes | 200 en pico | Conexiones SSE asíncronas; cada una consume poco mientras espera |
| Peticiones al LLM | 20 en toda la cuenta | `asyncio.Semaphore` global + cola acotada |

El semáforo es **de proceso**, así que sólo es un límite real con un único
worker de uvicorn. Con varios workers habría que coordinarlos, y sin Redis eso
significa una tabla de arrendamientos en SQLite. Está descartado por alcance y
documentado en `DECISIONES.md`.

Con 200 usuarios y 20 huecos, la cola es la parte visible del sistema: por eso
existe el evento `queued`, un tiempo máximo de espera y un `503` honesto
cuando la cola supera su capacidad. Preferimos rechazar rápido a acumular
conexiones colgadas.

**Coste por token:** contexto acotado, `k` de recuperación bajo, historial
truncado a los últimos turnos y caché de respuestas por hash de
`(tenant, pregunta normalizada, versión del índice)`.

---

## 6. Seguridad

### Aislamiento entre tenants

El aislamiento **no depende del prompt**. Se apoya en tres capas:

1. `tenant_id` sale del JWT firmado, nunca del cuerpo de la petición.
2. Todo acceso a datos pasa por repositorios que reciben el `TenantContext` y
   aplican el filtro en SQL.
3. Ninguna herramienta expuesta al modelo acepta `tenant_id` como parámetro.
   **El modelo no tiene forma de expresar "dame datos del tenant B"**, aunque
   un documento se lo ordene.

### Contenido recuperado como datos, no como instrucciones

Los chunks se inyectan dentro de delimitadores con una regla explícita en el
sistema: nada dentro de esos bloques es una instrucción. Durante la ingesta,
`rag/guard.py` detecta patrones de inyección (apelaciones a "instrucción
prioritaria", peticiones de ignorar restricciones previas, referencias a otros
tenants) y marca el chunk con `is_suspicious`. El chunk se sigue indexando
—ocultarlo sería mentir sobre el corpus— pero se degrada su ranking y queda
visible en el admin de Django.

### Resto de controles

- JWT HS256 con TTL corto; claims mínimos.
- `customer_email` enmascarado en logs siempre, y en respuestas cuando el
  usuario no es agente de soporte.
- Validación de entrada con Pydantic en todos los endpoints.
- Contenedores con usuario no root.
- Secretos sólo por variables de entorno; `.env` fuera del repositorio.
- CORS cerrado: nginx sirve frontend y API en el mismo origen.
- Límite básico de peticiones por usuario, en memoria.

---

## 7. Estructura del repositorio

```
att_assistant_challenge/
├── docker-compose.yml
├── .env.example
├── Makefile
├── .gitignore
├── README.md
|── ARQUITECTURA.md
|── DECISIONES.md
|── NO_HICE.md
├── backend_django/
│   ├── manage.py
│   ├── config/                 settings, urls, wsgi
│   └── core/
│       ├── models.py           los 5 necesarios + 3 añadidos
│       ├── admin.py
│       ├── auth_jwt.py         emisión de tokens
│       ├── pdf_factory.py      generación y extracción de PDF
│       ├── seed_content.py     extractos + relleno
│       ├── ingestion/          chunker, guard, fts  (escritura)
│       └── management/commands/
│           ├── seed_demo.py
│           └── ingest_docs.py
├── service_ai/
│   ├── main.py                 app FastAPI, Swagger en /docs
│   ├── config.py               settings tipadas desde .env
│   ├── deps.py                 TenantContext desde el JWT
│   ├── api/                    routes_chat, routes_health, sse
│   ├── llm/                    base, fake, openai, anthropic, factory
│   ├── rag/                    retriever, prompt  (lectura)
│   ├── tools/                  orders, tickets, registry
│   ├── db/                     engine, repositories
│   └── tests/
├── frontend/
│   └── src/                    Chat, useSSEChat, CitationList, api

```

---

## 8. Camino a producción

Lo que cambia cuando esto deja de ser un MVP, en orden:

1. **Postgres.** Cambiar `DATABASE_URL`, sustituir FTS5 por `tsvector` + GIN.
   Sólo toca `Retriever` y las migraciones.
2. **Concurrencia distribuida.** Varios workers exigen coordinar el límite de
   20; con Postgres, un advisory lock lo resuelve sin infraestructura nueva.
3. **Ingesta asíncrona.** Un PDF de 400 páginas no debe procesarse en el
   request. Con Postgres, `SKIP LOCKED` da una cola sin broker.
4. **Recuperación híbrida.** Embeddings + BM25 con fusión de rangos.
5. **Observabilidad.** Tokens y coste por tenant, latencia por etapa, tasa de
   escalado como señal de calidad del corpus.
