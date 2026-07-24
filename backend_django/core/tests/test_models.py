from decimal import Decimal

from django.db.utils import IntegrityError
from django.test import TestCase
from django.utils import timezone

from core.models import Document, DocumentChunk, Order, Tenant


class ModelTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug="acme", name="Acme SA")

    def test_la_referencia_de_pedido_es_unica(self):
        Order.objects.create(
            tenant=self.tenant,
            reference="ACME-000001",
            customer_email="c@example.com",
            total_amount=Decimal("10.50"),
            placed_at=timezone.now(),
        )
        with self.assertRaises(IntegrityError):
            Order.objects.create(
                tenant=self.tenant,
                reference="ACME-000001",
                customer_email="otro@example.com",
                total_amount=Decimal("1.00"),
                placed_at=timezone.now(),
            )

    def test_el_importe_conserva_los_decimales(self):
        order = Order.objects.create(
            tenant=self.tenant,
            reference="ACME-000002",
            customer_email="c@example.com",
            total_amount=Decimal("1234.56"),
            placed_at=timezone.now(),
        )
        order.refresh_from_db()
        self.assertEqual(order.total_amount, Decimal("1234.56"))

    def test_no_puede_haber_dos_chunks_con_el_mismo_ordinal(self):
        doc = Document.objects.create(tenant=self.tenant, title="Politicas", filename="p.pdf")
        DocumentChunk.objects.create(
            tenant=self.tenant, document=doc, ordinal=0, text="a", page_start=1, page_end=1
        )
        with self.assertRaises(IntegrityError):
            DocumentChunk.objects.create(
                tenant=self.tenant, document=doc, ordinal=0, text="b", page_start=2, page_end=2
            )
