# Pagamento via Pix copia-e-cola com aprovação manual, sem gateway

O AreaMais (projeto de referência) confirma pagamento automaticamente via webhook de um gateway (Asaas). A Fire Conference não integra nenhum gateway de pagamento: gera um Pix copia-e-cola dinâmico por inscrição e exige que o inscrito anexe um comprovante, que um aprovador de pagamento revisa manualmente antes de confirmar a inscrição. Decidido para evitar o custo e a complexidade de integrar um gateway para o volume esperado do evento — a conciliação manual é aceitável nessa escala.
