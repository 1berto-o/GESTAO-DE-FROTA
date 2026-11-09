"""
Cria o primeiro administrador somente se o banco não tiver nenhum usuário.

Uso (não roda automaticamente no entrypoint):

    python manage.py criar_admin_inicial --matricula 000001 --nome "Administrador" --password '...'

Se já existir qualquer usuário, o comando encerra sem alterar dados.
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

Usuario = get_user_model()


class Command(BaseCommand):
    help = 'Cria o administrador inicial apenas em banco sem usuários.'

    def add_arguments(self, parser):
        parser.add_argument('--matricula', required=True)
        parser.add_argument('--nome', required=True)
        parser.add_argument('--password', required=True)
        parser.add_argument('--email', default='')

    def handle(self, *args, **options):
        if Usuario.objects.exists():
            raise CommandError(
                'Já existem usuários no banco. Abortado — nenhum dado foi alterado.'
            )
        matricula = options['matricula'].strip()
        nome = options['nome'].strip()
        password = options['password']
        email = (options.get('email') or '').strip() or None
        if not matricula or not nome or not password:
            raise CommandError('Informe matrícula, nome e senha.')
        if len(password) < 10:
            raise CommandError('Use uma senha com pelo menos 10 caracteres.')

        user = Usuario.objects.create_superuser(
            matricula=matricula,
            nome=nome,
            password=password,
            email=email,
        )
        self.stdout.write(self.style.SUCCESS(
            f'Administrador criado: matrícula={user.matricula} id={user.id}'
        ))
