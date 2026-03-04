import logging
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail

logger = logging.getLogger('contracts')


def _send_email(subject, message, recipients):
    emails = [email for email in recipients if email]
    if not emails:
        logger.info('Email not sent: no recipients for subject "%s"', subject)
        return 0

    try:
        logger.info(
            'Sending email "%s" to %s',
            subject,
            ', '.join(emails)
        )
        return send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            emails,
            fail_silently=False,
        )
    except Exception:
        logger.exception('Failed to send notification email')
        return 0


def _group_emails(group_name):
    User = get_user_model()
    return list(
        User.objects.filter(groups__name=group_name, email__isnull=False)
        .exclude(email='')
        .values_list('email', flat=True)
        .distinct()
    )


def _admin_emails():
    User = get_user_model()
    admin_emails = _group_emails('ADMIN')
    superuser_emails = list(
        User.objects.filter(is_superuser=True, email__isnull=False)
        .exclude(email='')
        .values_list('email', flat=True)
    )
    return list(set(admin_emails + superuser_emails))


def notify_contract_created(contract, actor):
    manager = contract.manager
    if not manager or not manager.email:
        return 0

    subject = f'[GestaoContrato] Novo contrato #{contract.id}'
    message = (
        'Voce foi designado como manager de um contrato.\n\n'
        f'Contrato: {contract.title}\n'
        f'ID: {contract.id}\n'
        f'Valor total: {contract.total_value}\n'
        f'Criado por: {actor.username}\n'
    )
    return _send_email(subject, message, [manager.email])


def notify_measurement_created(measurement, actor):
    contract = measurement.contract
    manager = contract.manager
    if not manager or not manager.email:
        return 0

    subject = f'[GestaoContrato] Nova medicao #{measurement.id}'
    message = (
        'Uma nova medicao foi criada para o contrato.\n\n'
        f'Contrato: {contract.title}\n'
        f'ID do contrato: {contract.id}\n'
        f'ID da medicao: {measurement.id}\n'
        f'Valor: {measurement.value}\n'
        f'Criado por: {actor.username}\n'
    )
    return _send_email(subject, message, [manager.email])


def notify_measurement_approved(measurement, actor):
    contract = measurement.contract
    recipients = _group_emails('FINANCEIRO')
    if not recipients:
        return 0

    subject = f'[GestaoContrato] Medicao aprovada #{measurement.id}'
    message = (
        'Uma medicao foi aprovada e esta pronta para pagamento.\n\n'
        f'Contrato: {contract.title}\n'
        f'ID do contrato: {contract.id}\n'
        f'ID da medicao: {measurement.id}\n'
        f'Valor: {measurement.value}\n'
        f'Aprovado por: {actor.username}\n'
    )
    return _send_email(subject, message, recipients)


def notify_payment_paid(payment, actor):
    contract = payment.contract
    manager = contract.manager
    if not manager or not manager.email:
        return 0

    subject = f'[GestaoContrato] Pagamento realizado #{payment.id}'
    message = (
        'Um pagamento foi realizado para seu contrato.\n\n'
        f'Contrato: {contract.title}\n'
        f'ID do contrato: {contract.id}\n'
        f'ID do pagamento: {payment.id}\n'
        f'Valor: {payment.amount}\n'
        f'Pago por: {actor.username}\n'
    )
    return _send_email(subject, message, [manager.email])


def notify_contract_closed(contract, actor):
    recipients = _admin_emails()
    if not recipients:
        return 0

    subject = f'[GestaoContrato] Contrato fechado #{contract.id}'
    message = (
        'Um contrato foi fechado.\n\n'
        f'Contrato: {contract.title}\n'
        f'ID: {contract.id}\n'
        f'Manager: {contract.manager.username}\n'
        f'Fechado por: {actor.username}\n'
    )
    return _send_email(subject, message, recipients)
