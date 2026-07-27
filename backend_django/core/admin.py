"""
Admin de Django. Es la herramienta diaria de operaciones, asi que prioriza
poder encontrar cosas rapido y ver el estado de la ingesta.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html

from .models import (
    Conversation,
    Document,
    DocumentChunk,
    Message,
    Order,
    Tenant,
    Ticket,
    User,
)


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("slug", "name", "n_orders", "n_documents", "created_at")
    search_fields = ("slug", "name")

    @admin.display(description="pedidos")
    def n_orders(self, obj):
        return obj.orders.count()

    @admin.display(description="documentos")
    def n_documents(self, obj):
        return obj.documents.count()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "tenant", "is_support_agent", "is_staff", "is_active")
    list_filter = ("tenant", "is_support_agent", "is_staff", "is_active")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Asistente de soporte", {"fields": ("tenant", "is_support_agent")}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Asistente de soporte", {"fields": ("tenant", "is_support_agent")}),
    )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("reference", "tenant", "status", "total_amount", "currency", "placed_at")
    list_filter = ("tenant", "status", "currency")
    search_fields = ("reference", "customer_email")
    date_hierarchy = "placed_at"
    list_select_related = ("tenant",)


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("id", "subject", "tenant", "status", "priority", "created_at", "resolved_at")
    list_filter = ("tenant", "status", "priority")
    search_fields = ("subject", "body", "resolution")
    date_hierarchy = "created_at"
    list_select_related = ("tenant", "order")


class DocumentChunkInline(admin.TabularInline):
    model = DocumentChunk
    extra = 0
    fields = ("ordinal", "page_start", "page_end", "is_suspicious", "suspicion_reason")
    readonly_fields = fields
    can_delete = False
    max_num = 0


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "tenant", "page_count", "ingest_status", "n_suspicious", "indexed_at")
    list_filter = ("tenant", "ingest_status")
    search_fields = ("title", "filename")
    inlines = [DocumentChunkInline]
    list_select_related = ("tenant",)

    @admin.display(description="chunks marcados")
    def n_suspicious(self, obj):
        n = obj.chunks.filter(is_suspicious=True).count()
        if not n:
            return "-"
        return format_html('<strong style="color:#b23c17">{}</strong>', n)


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    """
    Vista clave para la revision del corpus: el filtro por is_suspicious muestra
    los fragmentos que la ingesta marco como intento de inyeccion.
    """

    list_display = ("id", "document", "ordinal", "pages", "is_suspicious", "suspicion_reason")
    list_filter = ("tenant", "is_suspicious")
    search_fields = ("text",)
    readonly_fields = ("tenant", "document", "ordinal", "text", "page_start", "page_end", "char_count")
    list_select_related = ("document", "tenant")

    @admin.display(description="paginas")
    def pages(self, obj):
        return f"{obj.page_start}-{obj.page_end}"


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    fields = ("role", "content", "citations", "escalated_ticket", "created_at")
    readonly_fields = fields
    can_delete = False
    max_num = 0


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "tenant", "user", "updated_at")
    list_filter = ("tenant",)
    inlines = [MessageInline]
    list_select_related = ("tenant", "user")


admin.site.site_header = "atyt_assistant_challenge"
admin.site.site_title = "atyt_assistant"
admin.site.index_title = "Operaciones y base de conocimiento"
