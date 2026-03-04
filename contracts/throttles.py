"""
Custom throttle classes para rate limiting.

Define limites específicos por tipo de operação e usuário.
"""

from rest_framework.throttling import UserRateThrottle


class StandardUserThrottle(UserRateThrottle):
    """Limite padrão para usuários autenticados.

    Operações comuns (GET, lista): 1000 requisições/hora
    """
    scope = 'user'


class BurstUserThrottle(UserRateThrottle):
    """Limite rigoroso para operações sensíveis.

    Operações críticas (criação, exclusão, aprovação): 100 requisições/hora
    """
    scope = 'burst'


class WriteOperationThrottle(UserRateThrottle):
    """Limite específico para operações de escrita (POST, PUT, DELETE).

    Protege contra spam de criação/atualização de dados.
    """
    scope = 'write'


class AuditLogThrottle(UserRateThrottle):
    """Limite relaxado para consulta de logs de auditoria.

    Logs são read-only, risco baixo: 500 requisições/hora
    """
    scope = 'audit'
