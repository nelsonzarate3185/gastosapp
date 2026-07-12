from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from facturas.models import UserRole


class Command(BaseCommand):
    help = 'Inicializar UserRole para todos los usuarios existentes'

    def handle(self, *args, **options):
        usuarios = User.objects.all()
        creados = 0
        ya_existentes = 0

        for user in usuarios:
            rol, created = UserRole.objects.get_or_create(
                user=user,
                defaults={'role': 'usuario_normal', 'activo': True}
            )
            if created:
                creados += 1
                self.stdout.write(
                    self.style.SUCCESS(f'  Creado rol para {user.username}')
                )
            else:
                ya_existentes += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'\nCompletado: {creados} nuevos, {ya_existentes} ya existentes'
            )
        )
