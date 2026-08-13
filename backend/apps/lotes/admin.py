from django.contrib import admin, messages

from .models import Lote


@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
    list_display = ['nome', 'preco', 'limite_vagas', 'vagas_ocupadas', 'ativo']
    list_filter = ['ativo']
    search_fields = ['nome']
    readonly_fields = ['criado_em', 'atualizado_em']
    actions = ['ativar_lote', 'desativar_lotes']

    @admin.action(description='Ativar o lote selecionado (desativa os demais)')
    def ativar_lote(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, 'Selecione exatamente um lote para ativar.', level=messages.ERROR)
            return
        lote = queryset.first()
        lote.ativo = True
        lote.save()
        self.message_user(request, f'"{lote.nome}" está ativo agora; os demais foram desativados.')

    @admin.action(description='Desativar lotes selecionados')
    def desativar_lotes(self, request, queryset):
        updated = queryset.update(ativo=False)
        self.message_user(request, f'{updated} lote(s) desativado(s).')
