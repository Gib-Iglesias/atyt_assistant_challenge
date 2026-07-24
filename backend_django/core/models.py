"""
Modelo de datos.

Los cinco modelos del enunciado estan tal cual: no se ha quitado ni renombrado
ningun campo. Se han anadido tres modelos y tres campos, todos justificados en
docs/DECISIONES.md, seccion 6.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


# --------------------------------------------------------------------- enunciado
class Tenant(models.Model):
    """Cliente de la plataforma. Frontera dura de aislamiento de datos."""

    slug = models.SlugField(max_length=64, unique=True)
    name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["slug"]
        verbose_name = "tenant"
        verbose_name_plural = "tenants"

    def __str__(self) -> str:
        return f"{self.name} ({self.slug})"


class User(AbstractUser):
    """
    Usuario del sistema.

    tenant nulo significa personal global (superusuario). El enunciado deja el
    campo nullable sin explicar la semantica; se documenta la interpretacion en
    docs/DECISIONES.md, seccion 7.
    """

    tenant = models.ForeignKey(
        Tenant, null=True, blank=True, on_delete=models.SET_NULL, related_name="users"
    )
    is_support_agent = models.BooleanField(default=False)

    class Meta:
        ordering = ["username"]

    def __str__(self) -> str:
        return self.username


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendiente"
        PAID = "paid", "Pagado"
        SHIPPED = "shipped", "Enviado"
        DELIVERED = "delivered", "Entregado"
        CANCELLED = "cancelled", "Cancelado"
        REFUNDED = "refunded", "Reembolsado"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="orders")
    # El enunciado pide reference unica. Se respeta como unicidad global, aunque
    # en un sistema multi-tenant lo natural seria unica por tenant.
    reference = models.CharField(max_length=64, unique=True)
    customer_email = models.EmailField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="EUR")
    placed_at = models.DateTimeField()
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-placed_at"]
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["tenant", "customer_email"]),
            models.Index(fields=["tenant", "-placed_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.reference} [{self.status}]"


class Ticket(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Abierto"
        PENDING = "pending", "Pendiente"
        ESCALATED = "escalated", "Escalado"
        RESOLVED = "resolved", "Resuelto"

    class Priority(models.TextChoices):
        LOW = "low", "Baja"
        NORMAL = "normal", "Normal"
        HIGH = "high", "Alta"
        URGENT = "urgent", "Urgente"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="tickets")
    order = models.ForeignKey(
        Order, null=True, blank=True, on_delete=models.SET_NULL, related_name="tickets"
    )
    subject = models.CharField(max_length=255)
    body = models.TextField()
    resolution = models.TextField(blank=True, default="")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
    priority = models.CharField(max_length=16, choices=Priority.choices, default=Priority.NORMAL)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["tenant", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"#{self.pk} {self.subject}"


class Document(models.Model):
    """
    Documento de la base de conocimiento.

    Campos anadidos sobre el enunciado: file, checksum e ingest_status. Sin
    ellos no hay forma de saber si el PDF existe ni si ya fue indexado.
    """

    class IngestStatus(models.TextChoices):
        PENDING = "pending", "Pendiente"
        PROCESSING = "processing", "Procesando"
        INDEXED = "indexed", "Indexado"
        FAILED = "failed", "Fallido"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="documents")
    title = models.CharField(max_length=255)
    filename = models.CharField(max_length=255)
    page_count = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    file = models.FileField(upload_to="documents/", blank=True, null=True)
    checksum = models.CharField(max_length=64, blank=True, default="")
    ingest_status = models.CharField(
        max_length=16, choices=IngestStatus.choices, default=IngestStatus.PENDING
    )
    ingest_error = models.TextField(blank=True, default="")
    indexed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["tenant__slug", "title"]
        indexes = [models.Index(fields=["tenant", "ingest_status"])]

    def __str__(self) -> str:
        return f"{self.title} ({self.page_count} pag.)"


# ---------------------------------------------------------------------- anadidos
class DocumentChunk(models.Model):
    """
    Fragmento indexable de un documento.

    Los limites de pagina son lo que permite citar "documento X, pagina Y" en
    lugar de citar el documento entero. is_suspicious lo marca rag/guard.py
    durante la ingesta cuando el texto parece intentar dar instrucciones al
    asistente. Ver docs/DECISIONES.md, seccion 1.
    """

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="chunks")
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="chunks")
    ordinal = models.PositiveIntegerField()
    text = models.TextField()
    page_start = models.PositiveIntegerField()
    page_end = models.PositiveIntegerField()
    char_count = models.PositiveIntegerField(default=0)

    is_suspicious = models.BooleanField(default=False)
    suspicion_reason = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["document_id", "ordinal"]
        constraints = [
            models.UniqueConstraint(fields=["document", "ordinal"], name="uniq_chunk_por_documento")
        ]
        indexes = [
            models.Index(fields=["tenant", "document"]),
            models.Index(fields=["tenant", "is_suspicious"]),
        ]

    def __str__(self) -> str:
        return f"{self.document_id}#{self.ordinal} (p.{self.page_start}-{self.page_end})"


class Conversation(models.Model):
    """Hilo de chat. El enunciado no lo contempla pero pide un asistente conversacional."""

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="conversations")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="conversations")
    title = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [models.Index(fields=["tenant", "user", "-updated_at"])]

    def __str__(self) -> str:
        return self.title or f"Conversacion {self.pk}"


class Message(models.Model):
    class Role(models.TextChoices):
        USER = "user", "Usuario"
        ASSISTANT = "assistant", "Asistente"
        SYSTEM = "system", "Sistema"

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    role = models.CharField(max_length=16, choices=Role.choices)
    content = models.TextField()
    # [{document_id, title, page_start, page_end, score}, ...]
    citations = models.JSONField(default=list, blank=True)
    escalated_ticket = models.ForeignKey(
        Ticket, null=True, blank=True, on_delete=models.SET_NULL, related_name="messages"
    )
    prompt_tokens = models.PositiveIntegerField(default=0)
    completion_tokens = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["conversation_id", "created_at", "id"]
        indexes = [models.Index(fields=["conversation", "created_at"])]

    def __str__(self) -> str:
        return f"{self.role}: {self.content[:40]}"
