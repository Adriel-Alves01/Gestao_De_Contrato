import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django  # noqa: E402

django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from django.contrib.auth.models import Group  # noqa: E402

User = get_user_model()

# Superuser - credenciais via variaveis de ambiente
su_user = os.getenv('DJANGO_SUPERUSER_USERNAME', 'admin')
su_email = os.getenv('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
su_pass = os.getenv('DJANGO_SUPERUSER_PASSWORD')

if su_pass and not User.objects.filter(username=su_user).exists():
    User.objects.create_superuser(su_user, su_email, su_pass)
    print(f'superuser criado: {su_user}')
elif not su_pass:
    print('AVISO: DJANGO_SUPERUSER_PASSWORD nao definida, superuser nao criado')
else:
    print(f'superuser ja existe: {su_user}')

# Usuario de demonstracao com perfil GESTOR
demo_user = os.getenv('DEMO_USERNAME', 'Usuario_Teste')
demo_pass = os.getenv('DEMO_PASSWORD')

if demo_pass:
    u, created = User.objects.get_or_create(username=demo_user)
    if created:
        u.set_password(demo_pass)
        u.save()
        print(f'usuario demo criado: {demo_user}')
    else:
        print(f'usuario demo ja existe: {demo_user}')
    gestor_group, _ = Group.objects.get_or_create(name='GESTOR')
    u.groups.add(gestor_group)
    print(f'grupo GESTOR atribuido a {demo_user}')
else:
    print('AVISO: DEMO_PASSWORD nao definida, usuario demo nao criado')
