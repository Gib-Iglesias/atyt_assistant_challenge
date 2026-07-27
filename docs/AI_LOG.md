# Registro del Uso de Inteligencia Artificial

## 1. Herramientas Utilizadas y Áreas de Aplicación

El uso de asistentes de IA se mantuvo acotado para conservar el control total del diseño y la implementación, representando **menos del 40% del código final** del repositorio.

* **Claude (Anthropic):**
  * **Generación de Tests:** Elaboración de la suite inicial de pruebas integradas y unitarias en backend.
  * **Documentación Automática:** Estructuración preliminar de docstrings y esquemas de API.
  * **Depuración de Frontend:** Detección de errores de renderizado y manejo de estados en la interfaz.
  * **Coexistencia Django / FastAPI:** Validación de patrones para el uso simultáneo de Django (ORM/Admin) y FastAPI (servicio RAG/Streaming) compartiendo la misma base de datos.

* **Gemini (Google):**
  * **Edición y Refinamiento de Documentación:** Curación, corrección de tono y estructuración de los archivos de lectura principales (`README.md`, `DECISIONES.md`, `NO_HICE.md` y `AI_LOG.md`).
  * **Revisión de Consistencia:** Auditoría de código y documentación para garantizar alineación con las restricciones del enunciado.

* **Uso General de IA:**
  * Generación de *scaffolding* básico de archivos, armado de mocks para pruebas de interfaz y asistencia en la toma de decisiones para ejecutar las suites de testing integradas en contenedores Docker.

---

## 2. Casos de Salidas Incorrectas o Subóptimas de la IA

### Caso 1: Manejo de Concurrencia Multi-worker en SQLite (Claude)
* **Lo que propuso:** Para cumplir con el límite de 20 peticiones concurrentes, sugirió implementar una tabla de *leases* o bloqueos temporales directamente en SQLite para coordinar múltiples workers de Uvicorn.
* **Cómo se detectó:** Al revisar la arquitectura de SQLite, añadir escrituras adicionales en la base de datos para coordinar semáforos aumentaba exponencialmente la contención y los errores de `database is locked` bajo carga.
* **Qué se hizo en su lugar:** Se simplificó la arquitectura a **un solo worker asíncrono de alta concurrencia** controlado por un `asyncio.Semaphore(20)` en memoria. Esto garantizó el límite de concurrencia exacto sin añadir sobrecarga de escrituras a SQLite.

### Caso 2: Elección de Embeddings Locales sin Conexión (Gemini / Claude)
* **Lo que propuso:** La IA recomendó incluir un modelo de embeddings pequeño (`sentence-transformers`) corriendo en local para resolver la búsqueda semántica manteniendo la restricción offline.
* **Cómo se detectó:** Al evaluar la construcción del entorno, descargar el modelo y sus dependencias de PyTorch/ONNX incrementaba el tamaño de la imagen Docker en más de 1.5 GB y ralentizaba significativamente el tiempo del primer arranque (`docker compose up`).
* **Qué se hizo en su lugar:** Se optó por **SQLite FTS5 con ranking BM25** puro. Esto permitió cumplir con el requisito estricto de arranque rápido en máquina limpia, sin red, sin credenciales de API y manteniendo la imagen liviana.

---

## 3. Caso de Sugerencia Aceptada tras Evaluación (Cambio de Opinión)

### Caso 3:   Ejecución Integral de Tests sobre Contenedores Docker (Claude)
* **Idea inicial (Rechazo):** La intención original era ejecutar las pruebas directamente en el entorno local del desarrollador (venv) para tener iteraciones más rápidas durante el desarrollo.
* **Propuesta de la IA:** Claude sugirió estructurar la suite de pruebas para que corra **exclusivamente dentro del contenedor Docker de pruebas**, simulando el proceso de construcción en limpio.
* **Por qué se cambió de opinión:** Al evaluar las diferencias entre el entorno local (donde SQLite o bibliotecas del sistema podían variar) y el contenedor aislado, se reconoció que probar sobre Docker garantizaba el cumplimiento real de la restricción del enunciado ("funcionar en máquina limpia con un solo comando"). Se adoptó la sugerencia y se integraron las pruebas dentro del flujo de Docker.
