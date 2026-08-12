from django.contrib import admin

from .models import CheckinAuditLog, Cupom, Inscricao


@admin.register(Cupom)
class CupomAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'valor_desconto', 'limite_usos', 'usos_count']
    search_fields = ['codigo']


@admin.register(Inscricao)
class InscricaoAdmin(admin.ModelAdmin):
    list_display = ['nome_completo', 'lote', 'cupom', 'status', 'preco_final', 'checkin_em', 'criado_em']
    list_filter = ['status', 'lote', 'origem']
    search_fields = ['nome_completo', 'cpf', 'email', 'token']
    readonly_fields = ['token', 'criado_em', 'atualizado_em']


@admin.register(CheckinAuditLog)
class CheckinAuditLogAdmin(admin.ModelAdmin):
    list_display = ['inscricao', 'resultado', 'usuario', 'criado_em']
    list_filter = ['resultado']
    search_fields = ['inscricao__nome_completo', 'codigo_tentado']
    readonly_fields = ['inscricao', 'resultado', 'codigo_tentado', 'usuario', 'criado_em']
