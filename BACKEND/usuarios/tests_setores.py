from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.test import APITestCase

from usuarios.models import Setor, normalizar_nome_setor

Usuario = get_user_model()


class SetorAdminApiTests(APITestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(
            matricula='910001', nome='Admin Setor', password='AdminSenha9', is_admin=True,
        )
        self.func = Usuario.objects.create_user(
            matricula='910002', nome='Func Setor', password='SenhaForte9', is_admin=False,
        )

    def test_funcionario_nao_acessa(self):
        self.client.force_authenticate(user=self.func)
        resp = self.client.get('/api/usuarios/setores/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        resp = self.client.post('/api/usuarios/setores/1/transferir/', {}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_criar_listar_editar_desativar_sem_ativos(self):
        self.client.force_authenticate(user=self.admin)
        criar = self.client.post('/api/usuarios/setores/', {
            'nome': 'Operações',
            'descricao': 'Área operacional',
        }, format='json')
        self.assertEqual(criar.status_code, status.HTTP_201_CREATED)
        setor_id = criar.data['id']
        self.assertTrue(criar.data['ativo'])
        self.assertEqual(criar.data['nome'], 'Operações')

        dup = self.client.post('/api/usuarios/setores/', {
            'nome': 'operações',
        }, format='json')
        self.assertEqual(dup.status_code, status.HTTP_400_BAD_REQUEST)

        lista = self.client.get('/api/usuarios/setores/')
        self.assertEqual(lista.status_code, status.HTTP_200_OK)
        results = lista.data['results'] if isinstance(lista.data, dict) and 'results' in lista.data else lista.data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['usuarios_count'], 0)
        self.assertEqual(results[0]['usuarios_ativos_count'], 0)

        patch = self.client.patch(f'/api/usuarios/setores/{setor_id}/', {
            'descricao': 'Atualizado',
            'ativo': False,
        }, format='json')
        self.assertEqual(patch.status_code, status.HTTP_200_OK)
        self.assertFalse(patch.data['ativo'])

        ativos = self.client.get('/api/usuarios/setores/', {'ativo': 'true'})
        ativos_lista = ativos.data['results'] if isinstance(ativos.data, dict) and 'results' in ativos.data else ativos.data
        self.assertEqual(len(ativos_lista), 0)

    def test_desativar_bloqueado_com_usuario_ativo(self):
        setor = Setor.objects.create(nome='Manutenção', ativo=True)
        Usuario.objects.create_user(
            matricula='910010', nome='Ativo no Setor', password='SenhaForte9',
            setor=setor, is_admin=False, is_active=True,
        )
        self.client.force_authenticate(user=self.admin)
        resp = self.client.patch(
            f'/api/usuarios/setores/{setor.id}/',
            {'ativo': False},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('ativo', resp.data)
        setor.refresh_from_db()
        self.assertTrue(setor.ativo)

    def test_desativar_permite_somente_inativos_vinculados(self):
        setor = Setor.objects.create(nome='Arquivo Histórico', ativo=True)
        Usuario.objects.create_user(
            matricula='910011', nome='Inativo no Setor', password='SenhaForte9',
            setor=setor, is_admin=False, is_active=False,
        )
        self.client.force_authenticate(user=self.admin)
        resp = self.client.patch(
            f'/api/usuarios/setores/{setor.id}/',
            {'ativo': False},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data['ativo'])
        self.assertEqual(resp.data['usuarios_inativos_count'], 1)
        self.assertEqual(resp.data['usuarios_ativos_count'], 0)

    def test_listar_e_transferir_usuarios(self):
        origem = Setor.objects.create(nome='Origem', ativo=True)
        destino = Setor.objects.create(nome='Destino', ativo=True)
        u1 = Usuario.objects.create_user(
            matricula='910012', nome='Um', password='SenhaForte9', setor=origem,
        )
        u2 = Usuario.objects.create_user(
            matricula='910013', nome='Dois', password='SenhaForte9', setor=origem,
        )
        self.client.force_authenticate(user=self.admin)

        membros = self.client.get(f'/api/usuarios/setores/{origem.id}/usuarios/')
        self.assertEqual(membros.status_code, status.HTTP_200_OK)
        self.assertEqual(len(membros.data['usuarios']), 2)

        move = self.client.post(
            f'/api/usuarios/setores/{origem.id}/transferir/',
            {'usuario_ids': [u1.id], 'setor_destino_id': destino.id},
            format='json',
        )
        self.assertEqual(move.status_code, status.HTTP_200_OK)
        self.assertEqual(move.data['atualizados'], 1)
        u1.refresh_from_db()
        self.assertEqual(u1.setor_id, destino.id)

        remove = self.client.post(
            f'/api/usuarios/setores/{origem.id}/transferir/',
            {'usuario_ids': [u2.id], 'setor_destino_id': None},
            format='json',
        )
        self.assertEqual(remove.status_code, status.HTTP_200_OK)
        u2.refresh_from_db()
        self.assertIsNone(u2.setor_id)

        # Agora origem sem ativos → pode desativar
        desativar = self.client.patch(
            f'/api/usuarios/setores/{origem.id}/',
            {'ativo': False},
            format='json',
        )
        self.assertEqual(desativar.status_code, status.HTTP_200_OK)

        # Destino inativo não aceita transferência
        destino.ativo = False
        destino.save(update_fields=['ativo', 'atualizado_em'])
        outro = Setor.objects.create(nome='Outro', ativo=True)
        u3 = Usuario.objects.create_user(
            matricula='910014', nome='Tres', password='SenhaForte9', setor=outro,
        )
        bad = self.client.post(
            f'/api/usuarios/setores/{outro.id}/transferir/',
            {'usuario_ids': [u3.id], 'setor_destino_id': destino.id},
            format='json',
        )
        self.assertEqual(bad.status_code, status.HTTP_400_BAD_REQUEST)

    def test_vincular_usuario_exige_setor_ativo(self):
        ativo = Setor.objects.create(nome='Logística', ativo=True)
        inativo = Setor.objects.create(nome='Arquivo', ativo=False)
        self.client.force_authenticate(user=self.admin)

        ok = self.client.post('/api/usuarios/', {
            'matricula': '910003',
            'nome': 'Novo',
            'setor': ativo.id,
        }, format='json')
        self.assertEqual(ok.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ok.data['setor'], ativo.id)
        self.assertEqual(ok.data['setor_nome'], 'Logística')

        bad = self.client.post('/api/usuarios/', {
            'matricula': '910004',
            'nome': 'Inválido',
            'setor': inativo.id,
        }, format='json')
        self.assertEqual(bad.status_code, status.HTTP_400_BAD_REQUEST)

        texto = self.client.post('/api/usuarios/', {
            'matricula': '910005',
            'nome': 'Texto Livre',
            'setor': 'Inventado',
        }, format='json')
        self.assertEqual(texto.status_code, status.HTTP_400_BAD_REQUEST)

    def test_normalizacao_case_insensitive(self):
        self.assertEqual(normalizar_nome_setor('  Setor  A  '), 'setor a')
        a = Setor(nome='Setor A')
        a.save()
        b = Setor(nome='setor a')
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                b.save()
