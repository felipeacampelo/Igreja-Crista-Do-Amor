from django.contrib import admin

from .models import Lote


@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
    list_display = ['nome', 'preco', 'limite_vagas', 'vagas_ocupadas', 'ativo']
    list_filter = ['ativo']
    search_fields = ['nome']
    readonly_fields = ['criado_em', 'atualizado_em']
    actions = ['desativar_lotes']

    @admin.action(description='Desativar lotes selecionados')
    def desativar_lotes(self, request, queryset):
        updated = queryset.update(ativo=False)
        self.message_user(request, f'{updated} lote(s) desativado(s).')
