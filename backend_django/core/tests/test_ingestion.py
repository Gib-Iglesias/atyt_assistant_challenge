"""
Prueba de extremo a extremo de la ingesta sobre un PDF generado de verdad, y la
comprobacion que mas pesa en la entrega: la busqueda nunca devuelve fragmentos
de otro tenant.
"""
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.test import TestCase

from core.ingestion import fts
from core.models import Document, DocumentChunk, Tenant
from core.pdf_factory import build_pdf
from core.seed_content import GUIA_FACTURACION, POLITICA_REEMBOLSOS, parrafos_operativos


def _crear_documento(tenant: Tenant, titulo: str, semilla: str, paginas: int = 3) -> Document:
    import random

    nombre = f"{tenant.slug}_{titulo.lower().replace(' ', '_')}.pdf"
    destino = Path(settings.MEDIA_ROOT) / "documents" / nombre
    n, digest = build_pdf(
        destino,
        titulo=titulo,
        bloques=parrafos_operativos(random.Random(7), semillas=[semilla]),
        paginas_objetivo=paginas,
    )
    return Document.objects.create(
        tenant=tenant, title=titulo, filename=nombre, page_count=n,
        file=f"documents/{nombre}", checksum=digest,
    )


class IngestionTests(TestCase):
    def setUp(self):
        self.acme = Tenant.objects.create(slug="acme", name="Acme SA")
        self.globex = Tenant.objects.create(slug="globex", name="Globex")
        self.doc_acme = _crear_documento(self.acme, "Guia de facturacion", GUIA_FACTURACION)
        self.doc_globex = _crear_documento(self.globex, "Politica de reembolsos", POLITICA_REEMBOLSOS)
        call_command("ingest_docs", verbosity=0)

    def test_la_ingesta_deja_los_documentos_indexados(self):
        for doc in (self.doc_acme, self.doc_globex):
            doc.refresh_from_db()
            self.assertEqual(doc.ingest_status, Document.IngestStatus.INDEXED)
            self.assertIsNotNone(doc.indexed_at)
            self.assertGreater(doc.chunks.count(), 0)

    def test_la_inyeccion_del_corpus_queda_marcada(self):
        marcados = DocumentChunk.objects.filter(document=self.doc_acme, is_suspicious=True)
        self.assertGreaterEqual(marcados.count(), 1)
        self.assertTrue(marcados.first().suspicion_reason)

    def test_el_contenido_marcado_sigue_estando_indexado(self):
        # No se borra: el sistema debe resistirlo con el corpus envenenado dentro.
        self.assertGreater(DocumentChunk.objects.filter(is_suspicious=True).count(), 0)

    def test_la_busqueda_solo_devuelve_fragmentos_del_tenant(self):
        consulta = fts.preparar_consulta("reembolsos y facturacion")
        ids_acme = set(DocumentChunk.objects.filter(tenant=self.acme).values_list("id", flat=True))

        resultados = fts.buscar(consulta, tenant_id=self.acme.pk, limite=20)

        self.assertTrue(resultados)
        for fila in resultados:
            self.assertIn(fila["id"], ids_acme)

    def test_la_busqueda_de_un_tenant_no_ve_el_documento_del_otro(self):
        consulta = fts.preparar_consulta("reembolsos metodo de pago original")
        resultados = fts.buscar(consulta, tenant_id=self.globex.pk, limite=20)
        documentos = {fila["document_id"] for fila in resultados}
        self.assertNotIn(self.doc_acme.pk, documentos)

    def test_reindexar_no_duplica_fragmentos(self):
        antes = DocumentChunk.objects.count()
        call_command("ingest_docs", "--reindex", verbosity=0)
        self.assertEqual(DocumentChunk.objects.count(), antes)
