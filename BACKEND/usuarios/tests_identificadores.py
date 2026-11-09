from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from usuarios.validators import (
    matricula_e_valida,
    normalizar_matricula,
    normalizar_telefone,
    telefone_e_valido,
    validar_matricula,
    validar_telefone,
)
from django.core.exceptions import ValidationError

Usuario = get_user_model()


class MatriculaValidadorUnitTests(APITestCase):
    def test_aceita_digitos_e_preserva_zeros(self):
        self.assertEqual(validar_matricula('012345'), '012345')
        self.assertEqual(normalizar_matricula(' 012345 '), '012345')
        self.assertTrue(matricula_e_valida('012345'))
        self.assertNotEqual(validar_matricula('012345'), '12345')

    def test_rejeita_letras_e_simbolos(self):
        for valor in ('ABC123', '12 34', '12-34', '12.34', '12a', ''):
            with self.assertRaises(ValidationError):
                validar_matricula(valor)
            self.assertFalse(matricula_e_valida(valor))


class MatriculaApiTests(APITestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(
            matricula='900100', nome='Admin ID', password='AdminSenha9', is_admin=True,
        )
        self.client.force_authenticate(user=self.admin)

    def test_criar_matricula_numerica_com_zeros(self):
        resp = self.client.post('/api/usuarios/', {
            'matricula': '000789',
            'nome': 'Novo Func',
            'is_admin': False,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['matricula'], '000789')
        self.assertTrue(Usuario.objects.filter(matricula='000789').exists())
        self.assertFalse(Usuario.objects.filter(matricula='789').exists())

    def test_criar_matricula_com_letras_e_recusada(self):
        resp = self.client.post('/api/usuarios/', {
            'matricula': 'FUNC01',
            'nome': 'Inválido',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('matricula', resp.data)

    def test_criar_matricula_com_simbolos_e_recusada(self):
        resp = self.client.post('/api/usuarios/', {
            'matricula': '12-34',
            'nome': 'Inválido',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_com_matricula_numerica(self):
        Usuario.objects.create_user(
            matricula='000321', nome='Login Zero', password='SenhaForte9', is_admin=False,
        )
        self.client.credentials()
        ok = self.client.post('/api/usuarios/login/', {
            'matricula': '000321', 'password': 'SenhaForte9',
        }, format='json')
        self.assertEqual(ok.status_code, status.HTTP_200_OK)
        bad = self.client.post('/api/usuarios/login/', {
            'matricula': 'abc', 'password': 'SenhaForte9',
        }, format='json')
        self.assertIn(bad.status_code, (status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED))


class TelefoneValidadorTests(APITestCase):
    def test_normaliza_e_valida(self):
        self.assertEqual(normalizar_telefone('(11) 98765-4321'), '11987654321')
        self.assertEqual(normalizar_telefone('+55 11 98765-4321'), '+5511987654321')
        self.assertTrue(telefone_e_valido('11987654321'))
        self.assertFalse(telefone_e_valido('123'))
        self.assertFalse(telefone_e_valido('telefone'))
        self.assertEqual(validar_telefone(''), '')

    def test_api_rejeita_telefone_invalido(self):
        admin = Usuario.objects.create_user(
            matricula='900101', nome='Admin Tel', password='AdminSenha9', is_admin=True,
        )
        self.client.force_authenticate(user=admin)
        resp = self.client.post('/api/usuarios/', {
            'matricula': '900102',
            'nome': 'Com Tel',
            'telefone': 'abc-xyz',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('telefone', resp.data)

    def test_api_aceita_telefone_formatado(self):
        admin = Usuario.objects.create_user(
            matricula='900103', nome='Admin Tel2', password='AdminSenha9', is_admin=True,
        )
        self.client.force_authenticate(user=admin)
        resp = self.client.post('/api/usuarios/', {
            'matricula': '900104',
            'nome': 'Com Tel Ok',
            'telefone': '(11) 98888-7777',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['telefone'], '11988887777')


class PendenciasRecuperacaoTests(APITestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(
            matricula='900200', nome='Admin Pend', password='AdminSenha9', is_admin=True,
        )
        self.func = Usuario.objects.create_user(
            matricula='900201', nome='Func Pend', password='SenhaForte9', is_admin=False,
        )

    def test_pendencias_inclui_recuperacao_zero(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get('/api/usuarios/pendencias/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['recuperacao_senha']['pendentes'], 0)

    def test_pendencias_conta_solicitacao(self):
        self.client.post('/api/usuarios/recuperacao-senha/solicitar/', {
            'matricula': '900201',
        }, format='json')
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get('/api/usuarios/pendencias/')
        self.assertEqual(resp.data['recuperacao_senha']['pendentes'], 1)

    def test_funcionario_nao_ve_pendencias(self):
        self.client.force_authenticate(user=self.func)
        resp = self.client.get('/api/usuarios/pendencias/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
