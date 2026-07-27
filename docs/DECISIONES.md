# Decisiones

## 1. Análisis del Enunciado y Resolución de Conflictos

### Seguridad e Aislamiento Multi-tenant
* **Defensa contra Prompt Injection:** El documento de políticas (`Guía de facturación 7.1`) incluye una instrucción maliciosa diseñada para provocar fuga de datos entre tenants. La mitigación se implementó de forma **estructural en el sistema**:
  * El `tenant_id` se extrae únicamente del JWT firmado y es inmutable.
  * Las herramientas expuestas al modelo no aceptan `tenant_id` como parámetro, omitiéndolo de su vocabulario.
  * El filtrado se realiza estrictamente en la capa de datos/SQL y no mediante instrucciones en el prompt.
  * Durante la ingesta, los fragmentos sospechosos se marcan (`is_suspicious`) y se degrada su ranking para auditoría en el panel de administración.

### Almacenamiento y Concurrencia (SQLite)
* **Estrategia para el MVP:** Se utilizó SQLite atendiendo al requerimiento predeterminado. Para sostener lecturas concurrentes y evitar bloqueos por escritura, se habilitó el modo WAL (`Write-Ahead Logging`) junto con `busy_timeout`.
* **Abstracción de Persistencia:** Todo el acceso a datos se estructuró a través del ORM y `DATABASE_URL` para permitir la migración directa a PostgreSQL en producción. Las consultas FTS5 de SQLite quedaron encapsuladas en una clase aislada.

### Control de Concurrencia Global
* **Límite de 20 peticiones concurrentes:** Al prescindir de infraestructura externa como Redis, un semáforo asíncrono (`asyncio.Semaphore`) solo funciona a nivel de proceso.
* **Decisión:** Se configuró el servicio con **un solo worker de alta concurrencia** en `docker-compose.yml`, asegurando el cumplimiento estricto del límite sin agregar sobrecarga de escrituras en la base de datos.

### Recuperación RAG (BM25 sin Motores Externos)
* **Motor de Búsqueda:** Se implementó **SQLite FTS5** con ranking **BM25** sobre fragmentos de ~900 caracteres alineados a saltos de página.
* **Justificación:** Cumple con la restricción de arrancar el sistema en una máquina limpia sin conexión a red, sin llaves de API y sin infraestructura vectorial adicional.

### Extensiones al Modelo de Datos
* Sin modificar las tablas originales, se incorporaron los modelos `Conversation`, `Message` y `DocumentChunk` para dar soporte a la gestión del chat y la trazabilidad de citas por página.

---

## 2. Decisiones de Diseño e Infraestructura

### Autenticación y Autorización
* **JWT (HS256):** Django emite los tokens y FastAPI los valida mediante un secreto compartido. Mantiene a FastAPI *stateless* y garantiza la integridad inalterable del `tenant_id`.

### Streaming de Respuestas
* **Server-Sent Events (SSE):** Se seleccionó un endpoint `POST` devolviendo `text/event-stream` con eventos estructurados (`queued`, `token`, `citations`, `escalated`, `done`, `error`). Esto permite emitir las citas al finalizar la generación y enviar cabeceras `Authorization` estándar.

### Factoría de Proveedores de LLM
* **Patrón Factory:** Abstracción mediante la interfaz `LLMProvider` que conmuta entre `openai`, `anthropic`, `gemini`, `ollama` y una implementación local `fake` mediante variables de entorno (`LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`). La implementación `fake` genera respuestas streaming con los fragmentos recuperados para pruebas offline sin depender de llaves de API.

### Umbral de Escalado Automático
* **Calibración de Score:** Se estableció `RETRIEVAL_MIN_SCORE=1.5`. Basado en mediciones sobre el corpus inicial, este umbral permite separar los resultados relevantes de la búsqueda léxica y derivar a escalado automático los casos con baja coincidencia.

### Separación de Responsabilidades
* **Django (Ingesta y Operación):** Mantiene la propiedad del esquema, realiza el fragmentado de documentos, detecta inyecciones de prompt y expone la administración del sistema.
* **FastAPI (Recuperación y Servicio de IA):** Funciona exclusivamente como un motor de lectura de alto rendimiento sobre el índice procesado.
