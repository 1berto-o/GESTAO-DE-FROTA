from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from rest_framework import status
from rest_framework.test import APITestCase

from auditoria.models import RegistroAuditoria
from usuarios.models import SolicitacaoRecuperacaoSenha
from usuarios import recuperacao as svc

Usuario = get_user_model()


class RecuperacaoSenhaFluxoTests(APITestCase):
    SENHA = 'SenhaForteAtual9'
    SENHA_NOVA = 'NovaSenhaForte9'

    def setUp(self):
        self.admin = Usuario.objects.create_user(
            matricula='100003', nome='Admin Rec', password='AdminSenha9', is_admin=True,
        )
        self.func = Usuario.objects.create_user(
            matricula='100042', nome='Func Rec', password=self.SENHA, is_admin=False,
        )

    def test_solicitar_nao_revela_existencia(self):
        ok = self.client.post('/api/usuarios/recuperacao-senha/solicitar/', {
            'matricula': '100042',
        }, format='json')
        inexistente = self.client.post('/api/usuarios/recuperacao-senha/solicitar/', {
            'matricula': '100053',
        }, format='json')
        self.assertEqual(ok.status_code, status.HTTP_200_OK)
        self.assertEqual(inexistente.status_code, status.HTTP_200_OK)
        self.assertEqual(ok.data['detail'], inexistente.data['detail'])
        self.assertEqual(
            SolicitacaoRecuperacaoSenha.objects.filter(matricula='100042', status='pendente').count(),
            1,
        )
        self.assertFalse(
            SolicitacaoRecuperacaoSenha.objects.filter(matricula='100053').exists()
        )

    def test_cooldown_nao_duplica_pendente(self):
        self.client.post('/api/usuarios/recuperacao-senha/solicitar/', {'matricula': '100042'}, format='json')
        self.client.post('/api/usuarios/recuperacao-senha/solicitar/', {'matricula': '100042'}, format='json')
        self.assertEqual(
            SolicitacaoRecuperacaoSenha.objects.filter(matricula='100042', status='pendente').count(),
            1,
        )

    def test_funcionario_nao_lista_nem_aprova(self):
        self.client.post('/api/usuarios/recuperacao-senha/solicitar/', {'matricula': '100042'}, format='json')
        sol = SolicitacaoRecuperacaoSenha.objects.get(matricula='100042', status='pendente')
        self.client.force_authenticate(user=self.func)
        lista = self.client.get('/api/usuarios/recuperacao-senha/')
        self.assertEqual(lista.status_code, status.HTTP_403_FORBIDDEN)
        aprovar = self.client.post(f'/api/usuarios/recuperacao-senha/{sol.id}/aprovar/')
        self.assertEqual(aprovar.status_code, status.HTTP_403_FORBIDDEN)

    def test_fluxo_completo_aprovar_e_redefinir(self):
        self.client.post('/api/usuarios/recuperacao-senha/solicitar/', {'matricula': '100042'}, format='json')
        sol = SolicitacaoRecuperacaoSenha.objects.get(status='pendente')
        self.client.force_authenticate(user=self.admin)
        aprovar = self.client.post(f'/api/usuarios/recuperacao-senha/{sol.id}/aprovar/')
        self.assertEqual(aprovar.status_code, status.HTTP_200_OK)
        codigo = aprovar.data['codigo']
        self.assertEqual(len(codigo), svc.CODIGO_TAMANHO)
        sol.refresh_from_db()
        self.assertEqual(sol.status, 'aprovada')
        self.assertTrue(sol.codigo_hash)
        self.assertNotIn(codigo, sol.codigo_hash)
        self.assertNotEqual(codigo, sol.codigo_hash)

        # código não persiste em texto puro
        dump = str(SolicitacaoRecuperacaoSenha.objects.filter(pk=sol.pk).values()[0])
        self.assertNotIn(codigo, dump)

        self.client.credentials()
        redef = self.client.post('/api/usuarios/recuperacao-senha/redefinir/', {
            'matricula': '100042',
            'codigo': codigo,
            'password': self.SENHA_NOVA,
            'password_confirm': self.SENHA_NOVA,
        }, format='json')
        self.assertEqual(redef.status_code, status.HTTP_200_OK)
        self.func.refresh_from_db()
        self.assertTrue(self.func.check_password(self.SENHA_NOVA))
        self.assertFalse(self.func.check_password(self.SENHA))
        sol.refresh_from_db()
        self.assertEqual(sol.status, 'usada')
        self.assertEqual(sol.codigo_hash, '')

        # código de uso único
        reuso = self.client.post('/api/usuarios/recuperacao-senha/redefinir/', {
            'matricula': '100042',
            'codigo': codigo,
            'password': 'OutraSenhaForte9',
            'password_confirm': 'OutraSenhaForte9',
        }, format='json')
        self.assertEqual(reuso.status_code, status.HTTP_400_BAD_REQUEST)

        login = self.client.post('/api/usuarios/login/', {
            'matricula': '100042', 'password': self.SENHA_NOVA,
        }, format='json')
        self.assertEqual(login.status_code, status.HTTP_200_OK)

    def test_codigo_expirado(self):
        self.client.post('/api/usuarios/recuperacao-senha/solicitar/', {'matricula': '100042'}, format='json')
        sol = SolicitacaoRecuperacaoSenha.objects.get(status='pendente')
        self.client.force_authenticate(user=self.admin)
        codigo = self.client.post(f'/api/usuarios/recuperacao-senha/{sol.id}/aprovar/').data['codigo']
        sol.refresh_from_db()
        sol.codigo_expira_em = timezone.now() - timedelta(minutes=1)
        sol.save(update_fields=['codigo_expira_em'])
        self.client.credentials()
        resp = self.client.post('/api/usuarios/recuperacao-senha/redefinir/', {
            'matricula': '100042',
            'codigo': codigo,
            'password': self.SENHA_NOVA,
            'password_confirm': self.SENHA_NOVA,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_tentativas_excedidas(self):
        self.client.post('/api/usuarios/recuperacao-senha/solicitar/', {'matricula': '100042'}, format='json')
        sol = SolicitacaoRecuperacaoSenha.objects.get(status='pendente')
        self.client.force_authenticate(user=self.admin)
        self.client.post(f'/api/usuarios/recuperacao-senha/{sol.id}/aprovar/')
        self.client.credentials()
        for _ in range(svc.MAX_TENTATIVAS_CODIGO):
            resp = self.client.post('/api/usuarios/recuperacao-senha/redefinir/', {
                'matricula': '100042',
                'codigo': 'XXXXXXXXXX',
                'password': self.SENHA_NOVA,
                'password_confirm': self.SENHA_NOVA,
            }, format='json')
            self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        sol.refresh_from_db()
        self.assertEqual(sol.status, 'expirada')

    def test_rejeitar(self):
        self.client.post('/api/usuarios/recuperacao-senha/solicitar/', {'matricula': '100042'}, format='json')
        sol = SolicitacaoRecuperacaoSenha.objects.get(status='pendente')
        self.client.force_authenticate(user=self.admin)
        resp = self.client.post(
            f'/api/usuarios/recuperacao-senha/{sol.id}/rejeitar/',
            {'observacao': 'Documento pendente'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        sol.refresh_from_db()
        self.assertEqual(sol.status, 'rejeitada')

    def test_endpoint_legado_admin_desativado(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.post(
            f'/api/usuarios/{self.func.id}/redefinir-senha/',
            {'password': self.SENHA_NOVA, 'password_confirm': self.SENHA_NOVA},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_410_GONE)
        self.func.refresh_from_db()
        self.assertTrue(self.func.check_password(self.SENHA))

    def test_auditoria_nao_guarda_codigo_nem_senha(self):
        self.client.post('/api/usuarios/recuperacao-senha/solicitar/', {'matricula': '100042'}, format='json')
        sol = SolicitacaoRecuperacaoSenha.objects.get(status='pendente')
        self.client.force_authenticate(user=self.admin)
        codigo = self.client.post(f'/api/usuarios/recuperacao-senha/{sol.id}/aprovar/').data['codigo']
        self.client.credentials()
        self.client.post('/api/usuarios/recuperacao-senha/redefinir/', {
            'matricula': '100042',
            'codigo': codigo,
            'password': self.SENHA_NOVA,
            'password_confirm': self.SENHA_NOVA,
        }, format='json')
        for reg in RegistroAuditoria.objects.all():
            blob = f'{reg.descricao} {reg.detalhes} {reg.identificacao} {reg.justificativa}'
            self.assertNotIn(codigo, blob)
            self.assertNotIn(self.SENHA_NOVA, blob)
            self.assertNotIn(self.SENHA, blob)
