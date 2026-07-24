"""
Datos de ejemplo realistas y deterministas.

Objetivos que fija el enunciado: al menos 4 tenants con volumenes claramente
desiguales, del orden de miles de pedidos en total, y documentos que lleguen a
las 400 paginas. Se generan 40 tenants, que es la cifra de las restricciones,
con cuatro grandes que concentran el volumen.

Todo depende de SEED_RANDOM_SEED: dos ejecuciones producen exactamente los
mismos datos, lo que hace que los tests y las capturas sean reproducibles.
"""
from __future__ import annotations

import random
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from core.models import Document, Order, Tenant, Ticket, User
from core.pdf_factory import build_pdf
from core.seed_content import DOCUMENTOS_BASE, parrafos_operativos

# Los cuatro grandes, con volumenes deliberadamente desiguales entre si.
TENANTS_GRANDES = [
    ("acme", "Acme Distribucion SA", 1800, "EUR"),
    ("globex", "Globex Retail", 820, "USD"),
    ("initech", "Initech Servicios", 340, "EUR"),
    ("umbrella", "Umbrella Comercio", 150, "MXN"),
]

DOMINIOS = ["example.com", "correo.example", "mail.example", "cliente.example"]
NOMBRES = ["lucia", "mateo", "sofia", "diego", "valeria", "javier", "carmen", "andres",
           "paula", "ruben", "elena", "tomas", "irene", "hugo", "marta", "sergio"]
APELLIDOS = ["ruiz", "moreno", "campos", "vega", "solis", "duarte", "iglesias", "navarro",
             "pardo", "cano", "bravo", "gil", "leon", "prieto", "sanz", "rico"]

PESOS_ESTADO = [
    (Order.Status.DELIVERED, 38), (Order.Status.SHIPPED, 18), (Order.Status.PAID, 16),
    (Order.Status.PENDING, 12), (Order.Status.CANCELLED, 9), (Order.Status.REFUNDED, 7),
]

ASUNTOS = [
    "No he recibido la factura", "El pedido figura enviado pero no llega",
    "Solicitud de reembolso", "Cambio de talla en producto de promocion",
    "Error en la direccion de entrega", "Duplicidad en el cargo",
    "Consulta sobre plazos de devolucion", "Producto recibido defectuoso",
]

# Paginas por documento segun perfil. El manual de operaciones es el que cumple
# el requisito de llegar a 400 paginas.
PERFILES = {
    "full": {"base": 6, "manual": 400, "manual_secundario": 120, "con_manual": 2},
    "fast": {"base": 2, "manual": 8, "manual_secundario": 6, "con_manual": 1},
}


class Command(BaseCommand):
    help = "Carga datos de ejemplo realistas y deterministas (idempotente)."

    def add_arguments(self, parser):
        parser.add_argument("--profile", choices=["fast", "full"], default=None)
        parser.add_argument("--tenants", type=int, default=None)
        parser.add_argument("--flush", action="store_true", help="Borra los datos antes de sembrar.")

    def handle(self, *args, **options):
        perfil = (options["profile"] or settings.SEED_PROFILE or "full").lower()
        if perfil not in PERFILES:
            perfil = "full"
        n_tenants = options["tenants"] or settings.SEED_TENANTS
        rng = random.Random(settings.SEED_RANDOM_SEED)

        if options["flush"]:
            self.stdout.write("borrando datos existentes...")
            for modelo in (Ticket, Order, Document, Tenant):
                modelo.objects.all().delete()

        if Tenant.objects.exists() and not options["flush"]:
            self.stdout.write(self.style.WARNING("ya hay datos sembrados; nada que hacer"))
            self._asegurar_usuarios(rng)
            return

        self.stdout.write(f"perfil={perfil} tenants={n_tenants} semilla={settings.SEED_RANDOM_SEED}")

        tenants = self._crear_tenants(n_tenants, rng)
        self._asegurar_usuarios(rng)
        total_pedidos = self._crear_pedidos(tenants, rng)
        total_tickets = self._crear_tickets(tenants, rng)
        total_docs, total_paginas = self._crear_documentos(tenants, rng, PERFILES[perfil])

        self.stdout.write(self.style.SUCCESS(
            f"listo: {len(tenants)} tenants, {total_pedidos} pedidos, "
            f"{total_tickets} tickets, {total_docs} documentos ({total_paginas} paginas)"
        ))

    # ------------------------------------------------------------------ tenants
    def _crear_tenants(self, n_tenants: int, rng: random.Random) -> list[tuple[Tenant, int, str]]:
        tenants: list[tuple[Tenant, int, str]] = []
        for slug, nombre, volumen, moneda in TENANTS_GRANDES:
            tenant = Tenant.objects.create(slug=slug, name=nombre)
            tenants.append((tenant, volumen, moneda))

        # La cola larga: muchos tenants pequenos, que es como se ven estos
        # sistemas de verdad.
        for i in range(len(TENANTS_GRANDES) + 1, n_tenants + 1):
            nombre = f"Cliente {i:02d} SL"
            tenant = Tenant.objects.create(slug=slugify(f"cliente-{i:02d}"), name=nombre)
            tenants.append((tenant, rng.randint(8, 45), rng.choice(["EUR", "USD"])))
        self.stdout.write(f"  tenants: {len(tenants)}")
        return tenants

    # ----------------------------------------------------------------- usuarios
    def _asegurar_usuarios(self, rng: random.Random) -> None:
        admin, creado = User.objects.get_or_create(
            username="admin",
            defaults={"is_staff": True, "is_superuser": True, "email": "admin@example.com"},
        )
        if creado:
            admin.set_password("admin123")
            admin.save(update_fields=["password"])

        for slug, _nombre, _vol, _moneda in TENANTS_GRANDES[:2]:
            tenant = Tenant.objects.filter(slug=slug).first()
            if not tenant:
                continue
            usuario, creado = User.objects.get_or_create(
                username=f"agente_{slug}",
                defaults={
                    "tenant": tenant,
                    "is_support_agent": True,
                    "email": f"agente@{slug}.example",
                },
            )
            if creado:
                usuario.set_password("demo1234")
                usuario.save(update_fields=["password"])
        self.stdout.write("  usuarios: admin + agentes de demostracion")

    # ------------------------------------------------------------------ pedidos
    def _crear_pedidos(self, tenants, rng: random.Random) -> int:
        ahora = timezone.now()
        estados = [e for e, _ in PESOS_ESTADO]
        pesos = [p for _, p in PESOS_ESTADO]
        total = 0

        for tenant, volumen, moneda in tenants:
            lote: list[Order] = []
            for n in range(1, volumen + 1):
                cliente = f"{rng.choice(NOMBRES)}.{rng.choice(APELLIDOS)}@{rng.choice(DOMINIOS)}"
                importe = Decimal(str(round(rng.uniform(9.9, 1450.0), 2)))
                lote.append(Order(
                    tenant=tenant,
                    reference=f"{tenant.slug.upper()}-{n:06d}",
                    customer_email=cliente,
                    status=rng.choices(estados, weights=pesos, k=1)[0],
                    total_amount=importe,
                    currency=moneda,
                    placed_at=ahora - timedelta(
                        days=rng.randint(0, 540), hours=rng.randint(0, 23), minutes=rng.randint(0, 59)
                    ),
                    notes=rng.choice(["", "", "", "Cliente solicito factura por separado.",
                                      "Entrega en horario de tarde.", "Segundo intento de entrega."]),
                ))
            with transaction.atomic():
                Order.objects.bulk_create(lote, batch_size=500)
            total += len(lote)
        self.stdout.write(f"  pedidos: {total}")
        return total

    # ------------------------------------------------------------------ tickets
    def _crear_tickets(self, tenants, rng: random.Random) -> int:
        total = 0
        estados = [Ticket.Status.OPEN, Ticket.Status.PENDING,
                   Ticket.Status.ESCALATED, Ticket.Status.RESOLVED]
        pesos_estado = [30, 20, 12, 38]
        prioridades = [Ticket.Priority.LOW, Ticket.Priority.NORMAL,
                       Ticket.Priority.HIGH, Ticket.Priority.URGENT]
        pesos_prioridad = [22, 48, 22, 8]

        for tenant, _volumen, _moneda in tenants:
            referencias = list(
                Order.objects.filter(tenant=tenant).values_list("id", flat=True)
            )
            if not referencias:
                continue
            cuantos = max(1, int(len(referencias) * 0.12))
            lote: list[Ticket] = []
            for _ in range(cuantos):
                # Uno de cada seis tickets no nace de un pedido concreto.
                order_id = rng.choice(referencias) if rng.random() > 0.16 else None
                estado = rng.choices(estados, weights=pesos_estado, k=1)[0]
                resuelto = estado == Ticket.Status.RESOLVED
                lote.append(Ticket(
                    tenant=tenant,
                    order_id=order_id,
                    subject=rng.choice(ASUNTOS),
                    body="El cliente contacta por el canal de soporte y solicita revision del caso.",
                    resolution="Se aplico el procedimiento estandar y se confirmo con el cliente."
                    if resuelto else "",
                    status=estado,
                    priority=rng.choices(prioridades, weights=pesos_prioridad, k=1)[0],
                    resolved_at=timezone.now() - timedelta(days=rng.randint(0, 90)) if resuelto else None,
                ))
            with transaction.atomic():
                Ticket.objects.bulk_create(lote, batch_size=500)
            total += len(lote)
        self.stdout.write(f"  tickets: {total}")
        return total

    # --------------------------------------------------------------- documentos
    def _crear_documentos(self, tenants, rng: random.Random, perfil: dict) -> tuple[int, int]:
        raiz = Path(settings.MEDIA_ROOT) / "documents"
        raiz.mkdir(parents=True, exist_ok=True)
        total_docs = total_paginas = 0

        for indice, (tenant, _volumen, _moneda) in enumerate(tenants):
            # Los tres documentos de politica los tiene todo el mundo: son la
            # semilla que da el enunciado.
            for titulo, fichero, semilla in DOCUMENTOS_BASE:
                nombre = f"{tenant.slug}_{fichero}"
                destino = raiz / nombre
                paginas, digest = build_pdf(
                    destino,
                    titulo=f"{tenant.name} - {titulo}",
                    bloques=parrafos_operativos(random.Random(rng.random()), semillas=[semilla]),
                    paginas_objetivo=perfil["base"],
                )
                Document.objects.create(
                    tenant=tenant, title=titulo, filename=nombre, page_count=paginas,
                    file=f"documents/{nombre}", checksum=digest,
                )
                total_docs += 1
                total_paginas += paginas

            # Manuales largos solo para los primeros tenants: es lo que produce
            # el desnivel de volumen que pide el enunciado.
            if indice < perfil["con_manual"]:
                objetivo = perfil["manual"] if indice == 0 else perfil["manual_secundario"]
                nombre = f"{tenant.slug}_manual_operaciones.pdf"
                destino = raiz / nombre
                self.stdout.write(f"  generando {nombre} ({objetivo} paginas)...")
                paginas, digest = build_pdf(
                    destino,
                    titulo=f"{tenant.name} - Manual de operaciones",
                    bloques=parrafos_operativos(random.Random(rng.random())),
                    paginas_objetivo=objetivo,
                )
                Document.objects.create(
                    tenant=tenant, title="Manual de operaciones", filename=nombre,
                    page_count=paginas, file=f"documents/{nombre}", checksum=digest,
                )
                total_docs += 1
                total_paginas += paginas

        self.stdout.write(f"  documentos: {total_docs} ({total_paginas} paginas)")
        return total_docs, total_paginas
