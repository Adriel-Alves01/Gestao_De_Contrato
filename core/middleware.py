"""
Middleware para logging estruturado de requests.

Registra todas as requisições HTTP com:
- Request ID único
- Método HTTP, path, query params
- User (se autenticado)
- IP de origem
- Tempo de resposta
- Status code
"""

import logging
import time
import uuid
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('requests')


class RequestLoggingMiddleware(MiddlewareMixin):
    """Middleware que registra todas as requisições HTTP."""

    def process_request(self, request):
        """Executado antes da view processar o request."""
        # Gera ID único para correlacionar logs da mesma request
        request.request_id = str(uuid.uuid4())[:8]
        request.start_time = time.time()

        # Log da request entrando
        user_info = (
            f"User:{request.user.id}"
            if request.user.is_authenticated
            else "Anonymous"
        )
        ip_address = self.get_client_ip(request)

        logger.info(
            f"[{request.request_id}] → {request.method} {request.path} | "
            f"{user_info} | IP:{ip_address}"
        )

        return None

    def process_response(self, request, response):
        """Executado após a view processar e antes de retornar response."""
        if not hasattr(request, 'start_time'):
            return response

        # Calcula tempo de execução
        duration = time.time() - request.start_time
        duration_ms = int(duration * 1000)

        # Log da response saindo
        user_info = (
            f"User:{request.user.id}"
            if request.user.is_authenticated
            else "Anonymous"
        )

        log_level = logging.INFO
        if response.status_code >= 500:
            log_level = logging.ERROR
        elif response.status_code >= 400:
            log_level = logging.WARNING

        logger.log(
            log_level,
            f"[{request.request_id}] ← {request.method} {request.path} | "
            f"Status:{response.status_code} | {duration_ms}ms | {user_info}"
        )

        return response

    def process_exception(self, request, exception):
        """Executado quando ocorre exceção não tratada."""
        logger.error(
            f"[{request.request_id}]  EXCEPTION in "
            f"{request.method} {request.path} | "
            f"Error: {exception.__class__.__name__}: {str(exception)}",
            exc_info=True
        )
        return None

    @staticmethod
    def get_client_ip(request):
        """Extrai IP real do cliente (mesmo atrás de proxy)."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
