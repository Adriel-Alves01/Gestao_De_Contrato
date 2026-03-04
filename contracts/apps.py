from django.apps import AppConfig


class ContractsConfig(AppConfig):
    name = 'contracts'

    def ready(self):
        """Registra signals quando a aplicação está pronta."""
        import contracts.signals  # noqa
