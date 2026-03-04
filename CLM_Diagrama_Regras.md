# Mapa de Relações CLM - Contratos

## Diagrama de Entidades e Relacionamentos

![Diagrama ER](diagram.png)

## Regras de Negócio

1. Só é permitido um pagamento por medição.
2. Apenas medições aprovadas podem gerar pagamento.
3. Contrato com status "CLOSED" bloqueia novas medições.
4. Não é permitido aprovar uma medição mais de uma vez.
5. Não é permitido pagar uma medição rejeitada.
6. Pagamentos podem ter status "FAILED" em caso de erro no processamento financeiro.

## Entidades Principais

- **User**: Usuário do sistema, pode ser gestor, fornecedor, financeiro ou admin.
- **Contract**: Contrato, com valor total, saldo, datas, status e gestor responsável.
- **Measurement**: Medição vinculada ao contrato, com valor e status (PENDING, APPROVED, REJECTED).
- **Payment**: Pagamento referente à medição, com valor, status (PENDING, PAID, FAILED) e usuário criador.
- **Attachment**: Anexos vinculados ao contrato.
- **ContractStatusHistory**: Histórico de status do contrato.

---

Este documento serve como referência rápida para o desenvolvimento e validação das regras do sistema CLM.
