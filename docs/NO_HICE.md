# No Hice / Alcance Futuro

Este documento detalla las funcionalidades, optimizaciones y decisiones técnicas que quedaron fuera del alcance del MVP de 24 horas, así como la hoja de ruta planificada para llevar el sistema a una arquitectura lista para producción.

---

## 1. Limitaciones Técnicas y Puntos Excluidos en el MVP

### Recuperación y RAG
* **Búsqueda Semántica (Embeddings):** Se optó por BM25 puro para garantizar el arranque offline sin dependencias de red o modelos locales pesados. Quedó pendiente la implementación de vectores, lo que limita la precisión ante paráfrasis o sinónimos complejos.
* **Reranking:** No se incluyó una etapa de reordenamiento de contexto recuperado mediante un modelo secundario, dado el volumen inicial de fragmentos por consulta.
* **Procesamiento de PDF mediante OCR:** El sistema asume que los documentos cargados cuentan con capa de texto legible. Los archivos escaneados requieren una etapa previa de OCR.

### Escala e Infraestructura
* **Gestión de Concurrencia Multi-worker:** El semáforo de limitación (20 peticiones) se ejecuta en un solo proceso. En una arquitectura multi-worker se requerirá un orquestador coordinado (ej. Redis o tabla de leases).
* **Ingesta Asíncrona:** El procesamiento e indexación de archivos extensos (~400 páginas) ocurre de forma síncrona durante el sembrado inicial.
* **Persistencia en PostgreSQL:** La arquitectura utiliza SQLite para el MVP. Aunque el acceso está desacoplado mediante el ORM, la migración a Postgres requerirá sustituir FTS5 por `tsvector` + GIN y ajustar el pool de conexiones.

### Funcionalidades de Producto
* **Persistencia del Historial en UI:** Las entidades `Conversation` y `Message` están estructuradas en el backend, pero la interfaz de usuario no carga sesiones históricas anteriores.
* **Verificación de Identidad Explicita:** Se asumió que la validación del usuario final se gestiona previamente fuera del sistema por el agente de soporte.
* **Renovación Silenciosa de Tokens (Refresh Tokens):** La expiración del JWT obliga al usuario a autenticarse nuevamente.
* **Monitoreo de Costos por Tenant:** Se registra el proveedor seleccionado, pero no se implementó el conteo de tokens consumidos ni la contabilidad de costos asociada a cada tenant.

---

## 2. Hoja de Ruta y Fases de Desarrollo

### Fase 1: MVP (Estado Actual)
* Chat conversacional con RAG, streaming via SSE y citas por página.
* Aislamiento multi-tenant validado a nivel de base de datos y JWT.
* Motor de búsqueda FTS5 (BM25) integrado en SQLite.
* Interfaz de proveedor de LLM intercambiable por variables de entorno con modo `fake` offline.

### Fase 2: Producción e Infraestructura
* Migración de base de datos a PostgreSQL.
* Búsqueda híbrida (combinación de BM25 + Embeddings) con algoritmo de reranking.
* Procesamiento de ingesta asíncrono con barra de estado y colas de trabajo.
* Límite de concurrencia distribuido para arquitecturas de múltiples workers.
* Telemetría y observabilidad de consumo de tokens por tenant.

### Fase 3: Evolución de Producto
* Visualización e historial de conversaciones previas desde el cliente frontend.
* Panel UI para gestión de documentos (carga, versionado y reindexación).
* Módulo de feedback directo por parte del agente para evaluación de calidad de respuestas.

### Fase 4: Inteligencia Operativa
* Análisis de tasa de escalado para identificar vacíos en la documentación del sistema.
* Sugerencia automática de soluciones basada en tickets históricos similares.
* Sistema de alertas proactivas ante picos de consultas sobre temas específicos.

---

## 3. Principios Arquitectónicos Permanentes

* **Aislamiento Estructural:** La separación entre tenants debe ejecutarse siempre en la capa de datos (SQL/Repositorios) y nunca depender del prompt del modelo.
* **Tratamiento de Contexto:** El texto recuperado se trata estrictamente como datos no confiables y jamás como instrucciones ejecutables.
* **Desacoplamiento de Proveedores:** El acceso a los modelos de lenguaje debe mantenerse detrás de abstracciones (interfaces) con soporte de ejecución offline.
* **Configuración por Entorno:** Toda variación de infraestructura o credenciales debe gestionarse mediante variables de entorno.
