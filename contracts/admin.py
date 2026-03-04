from django.contrib import admin
from .models import (
    Contract,
    Measurement,
    Payment,
    Attachment,
    ContractStatusHistory,
    AuditLog,
)


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'status', 'manager', 'total_value', 'created_at', 'is_deleted'
    )
    list_filter = ('status', 'is_deleted', 'created_at')
    search_fields = ('title', 'description')
    readonly_fields = (
        'created_at', 'updated_at', 'is_deleted', 'deleted_at', 'deleted_by'
    )


@admin.register(Measurement)
class MeasurementAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'contract', 'value', 'status', 'created_by', 'created_at'
    )
    list_filter = ('status', 'created_at')
    search_fields = ('contract__title', 'description')
    readonly_fields = (
        'created_at', 'updated_at', 'approved_at', 'rejected_at'
    )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'contract', 'measurement', 'amount', 'status',
        'created_by', 'created_at'
    )
    list_filter = ('status', 'created_at')
    search_fields = ('contract__title', 'measurement__description')
    readonly_fields = ('created_at', 'updated_at', 'paid_at')


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'contract', 'uploaded_by', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('contract__title',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ContractStatusHistory)
class ContractStatusHistoryAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'contract', 'old_status', 'new_status',
        'changed_by', 'changed_at'
    )
    list_filter = ('changed_at',)
    search_fields = ('contract__title',)
    readonly_fields = ('changed_at',)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'action', 'model_name', 'object_id', 'user', 'timestamp'
    )
    list_filter = ('action', 'model_name', 'timestamp')
    search_fields = ('object_display', 'user__username')
    readonly_fields = (
        'id', 'action', 'model_name', 'object_id', 'object_display',
        'user', 'changes', 'timestamp', 'ip_address'
    )

    def has_add_permission(self, request):
        # AuditLog é read-only, não pode ser criado manualmente
        return False

    def has_delete_permission(self, request, obj=None):
        # AuditLog é read-only, não pode ser deletado
        return False

    def has_change_permission(self, request, obj=None):
        # AuditLog é read-only, não pode ser editado
        return False
