# Decisiones Arquitectónicas

## 1. Análisis del Enunciado y Resolución de Conflictos

### Seguridad e Aislamiento Multi-tenant
* **Detección de Prompt Injection:** El documento de políticas (`Guía de facturación 7.1`) incluye un intento deliberado de fuga de datos cross-tenant. La mitigación implementada es **estructural y no basada en el LLM**:
  * El `tenant_id` se extrae exclusivamente del JWT firmado y no se puede modificar por petición.
  * Ninguna herramienta expuesta al modelo acepta `tenant_id` como parámetro, imposibilitando el acceso cruzado.
  * El filtrado de datos se aplica a nivel de capa de datos / SQL y no mediante instrucciones en el prompt.
  * La ingesta analiza los fragmentos y marca como sospechosos los datos potencialmente maliciosos (`is_suspicious`), manteniendo el registro en administración para auditoría sin contaminar las respuestas.

### Almacenamiento y Concurrencia (SQLite)
* **Persistencia en MVP:** Aunque el enunciado especifica SQLite para una carga proyectada de 200 usuarios concurrentes, SQLite presenta limitaciones nativas de un solo escritor.
* **Mitigación:** Se habilitó el modo WAL (`Write-Ahead Logging`) y `busy_timeout`. El acceso se centralizó a través de un ORM (`DATABASE_URL`) para facilitar la transición directa a PostgreSQL en producción. La funcionalidad de FTS5 se encapsuló en una sola clase para evitar acoplamiento con la sintaxis de SQLite.

### Control de Concurrencia Global
* **Límite de 20 peticiones concurrentes:** Al restringir el uso de infraestructura externa (como Redis), un semáforo asíncrono (`asyncio.Semaphore`) solo es efectivo dentro del mismo proceso.
* **Decisión:** Se configuró el servicio asíncrono con **un solo worker de alta concurrencia** en `docker-compose.yml` para garantizar el límite global exacto sin sobrecargar la base de datos con tablas de arrendamiento.

### Estrategia de Búsqueda y RAG (BM25 vs. Embeddings)
* **Requisito "Sin motores de búsqueda externos":** Se interpretó como la ausencia de servicios/servidores dedicados adicionales.
* **Selección de Motor:** Se utilizó **SQLite FTS5** con ranking **BM25**. Esto permite ejecutar la búsqueda léxica y el procesamiento de documentos (~400 páginas) de manera totalmente autónoma, sin depender de red, GPUs locales pesadas ni servicios de vectores externos.

### Extensiones al Modelo de Datos
* Para dar soporte al comportamiento conversacional y al tracking de citas por página sin alterar las tablas originales, se añadieron las siguientes entidades: `Conversation`, `Message` y `DocumentChunk`.

---

## 2. Decisiones de Diseño de Software

### Autenticación y Autorización
* **JWT (HS256):** Emitido por Django y validado por FastAPI mediante una clave secreta compartida. Esto permite mantener a FastAPI como un servicio apátrida (*stateless*), asegurando que el `tenant_id` viaje firmado de forma inmutable.

### Estrategia de Streaming
* **Server-Sent Events (SSE) con eventos tipados:** Se implementó una respuesta `text/event-stream` con eventos estructurados (`queued`, `token`, `citations`, `escalated`, `done`, `error`). Se descartaron WebSockets por complejidad innecesaria y `EventSource` nativo por la incapacidad de enviar cabeceras de autorización `Bearer`.

### Abstracción del Proveedor de LLM
* **Patrón Factory:** Interfaz `LLMProvider` parametrizable vía variables de entorno (`LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`). Incluye integraciones para `openai`, `anthropic`, `gemini`, `ollama` y una implementación local `fake` que simula streaming palabra por palabra utilizando los chunks recuperados por BM25 para pruebas offline.

### Separación de Responsabilidades entre Servicios
* **Ingesta (Django):** Django actúa como el dueño del esquema de datos. La fragmentación, la construcción del índice FTS5 y la detección de inyecciones ocurren dentro de `backend_django`.
* **Recuperación (FastAPI):** FastAPI funciona únicamente como un motor de lectura y consulta sobre el índice ya procesado.