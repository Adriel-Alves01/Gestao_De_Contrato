import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django  # noqa: E402

django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from django.contrib.auth.models import Group  # noqa: E402

User = get_user_model()

if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin')
    print('superuser criado: admin/admin')
else:
    print('superuser ja existe: admin')

# Usuario de demonstracao com perfil GESTOR
u, created = User.objects.get_or_create(username='Usuario_Teste')
if created:
    u.set_password('Teste124')
    u.save()
    print('usuario demo criado: Usuario_Teste/Teste124')
else:
    print('usuario demo ja existe: Usuario_Teste')

gestor_group, _ = Group.objects.get_or_create(name='GESTOR')
u.groups.add(gestor_group)
print('grupo GESTOR atribuido ao Usuario_Teste')
