"""
Ingesta: PDF -> texto por pagina -> fragmentos -> indice FTS5.

Corre en Django y no en el servicio de IA porque es escritura sobre el esquema,
y el dueno del esquema es Django. El servicio de IA solo lee el indice.
"""
from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.ingestion import fts, guard
from core.ingestion.chunker import trocear_documento
from core.models import Document, DocumentChunk
from core.pdf_factory import extraer_paginas


class Command(BaseCommand):
    help = "Extrae, fragmenta e indexa los documentos pendientes."

    def add_arguments(self, parser):
        parser.add_argument("--reindex", action="store_true", help="Reprocesa todos los documentos.")
        parser.add_argument("--document", type=int, default=None, help="Ingesta un solo documento.")
        parser.add_argument("--chunk-size", type=int, default=None)
        parser.add_argument("--chunk-overlap", type=int, default=None)

    def handle(self, *args, **options):
        tam = options["chunk_size"] or int(getattr(settings, "CHUNK_SIZE_CHARS", 900))
        solape = options["chunk_overlap"] or int(getattr(settings, "CHUNK_OVERLAP_CHARS", 150))

        docs = Document.objects.select_related("tenant")
        if options["document"]:
            docs = docs.filter(pk=options["document"])
        elif not options["reindex"]:
            docs = docs.exclude(ingest_status=Document.IngestStatus.INDEXED)

        docs = list(docs)
        if not docs:
            self.stdout.write("no hay documentos pendientes")
            fts.crear_indice()
            return

        fts.crear_indice()
        total_chunks = total_sospechosos = 0

        for doc in docs:
            try:
                n_chunks, n_sospechosos = self._ingerir(doc, tam, solape)
            except Exception as exc:  # noqa: BLE001 - un documento roto no debe tumbar la ingesta
                doc.ingest_status = Document.IngestStatus.FAILED
                doc.ingest_error = str(exc)[:2000]
                doc.save(update_fields=["ingest_status", "ingest_error"])
                self.stderr.write(self.style.ERROR(f"  fallo en {doc.filename}: {exc}"))
                continue
            total_chunks += n_chunks
            total_sospechosos += n_sospechosos

        indexados = fts.reconstruir()
        self.stdout.write(self.style.SUCCESS(
            f"ingesta terminada: {len(docs)} documentos, {total_chunks} fragmentos, "
            f"{indexados} en el indice"
        ))
        if total_sospechosos:
            # Es una senal para operaciones, no un error: el corpus contiene
            # contenido que intenta dar instrucciones al asistente.
            self.stdout.write(self.style.WARNING(
                f"  {total_sospechosos} fragmentos marcados como posible inyeccion "
                f"(revisables en el admin, filtro 'is suspicious')"
            ))

    def _ingerir(self, doc: Document, tam: int, solape: int) -> tuple[int, int]:
        ruta = Path(settings.MEDIA_ROOT) / (doc.file.name if doc.file else f"documents/{doc.filename}")
        if not ruta.exists():
            raise FileNotFoundError(f"no existe el fichero {ruta}")

        doc.ingest_status = Document.IngestStatus.PROCESSING
        doc.save(update_fields=["ingest_status"])

        paginas = extraer_paginas(ruta)
        fragmentos = trocear_documento(paginas, tam=tam, solape=solape)

        objetos: list[DocumentChunk] = []
        sospechosos = 0
        for fragmento in fragmentos:
            marcado, motivo = guard.analizar(fragmento.text)
            sospechosos += int(marcado)
            objetos.append(DocumentChunk(
                tenant_id=doc.tenant_id,
                document=doc,
                ordinal=fragmento.ordinal,
                text=fragmento.text,
                page_start=fragmento.page_start,
                page_end=fragmento.page_end,
                char_count=fragmento.char_count,
                is_suspicious=marcado,
                suspicion_reason=motivo,
            ))

        with transaction.atomic():
            DocumentChunk.objects.filter(document=doc).delete()
            DocumentChunk.objects.bulk_create(objetos, batch_size=500)
            doc.page_count = len(paginas)
            doc.ingest_status = Document.IngestStatus.INDEXED
            doc.ingest_error = ""
            doc.indexed_at = timezone.now()
            doc.save(update_fields=["page_count", "ingest_status", "ingest_error", "indexed_at"])

        marca = f" ({sospechosos} marcados)" if sospechosos else ""
        self.stdout.write(f"  {doc.filename}: {len(paginas)} pag. -> {len(objetos)} fragmentos{marca}")
        return len(objetos), sospechosos
