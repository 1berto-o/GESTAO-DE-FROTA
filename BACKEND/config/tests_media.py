import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from config.media_access import assinar_caminho, normalizar_caminho_relativo

Usuario = get_user_model()

_PNG = (
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
    b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00'
    b'\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18'
    b'\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
)


class MediaProtegidaTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._tmpdir = tempfile.TemporaryDirectory()
        cls._media = cls._tmpdir.name

    @classmethod
    def tearDownClass(cls):
        cls._tmpdir.cleanup()
        super().tearDownClass()

    def setUp(self):
        self.override = override_settings(
            MEDIA_ROOT=self._media,
            MEDIA_URL='/media/',
            MEDIA_URL_TOKEN_MAX_AGE=3600,
            USE_SUPABASE_STORAGE=False,
        )
        self.override.enable()
        self.addCleanup(self.override.disable)

        self.admin = Usuario.objects.create_user(
            matricula='920001', nome='Admin Media', password='AdminSenha9', is_admin=True,
        )
        self.func = Usuario.objects.create_user(
            matricula='920002', nome='Func Media', password='SenhaForte9', is_admin=False,
        )
        self.client = APIClient()
        self.relativo = 'veiculos/foto-teste.png'
        alvo = Path(self._media) / self.relativo
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_bytes(_PNG)

    def test_anonimo_sem_token_bloqueado(self):
        resp = self.client.get(f'/media/{self.relativo}')
        self.assertEqual(resp.status_code, 403)

    def test_token_assinado_permite(self):
        token = assinar_caminho(self.relativo)
        resp = self.client.get(f'/media/{self.relativo}', {'t': token})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Cache-Control'], 'private, no-store')

    def test_token_de_outro_arquivo_rejeitado(self):
        token = assinar_caminho('veiculos/outro.png')
        resp = self.client.get(f'/media/{self.relativo}', {'t': token})
        self.assertEqual(resp.status_code, 403)

    def test_jwt_autenticado_veiculo(self):
        access = str(RefreshToken.for_user(self.func).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        resp = self.client.get(f'/media/{self.relativo}')
        self.assertEqual(resp.status_code, 200)

    def test_path_traversal_rejeitado(self):
        with self.assertRaises(ValueError):
            normalizar_caminho_relativo('../etc/passwd')
        resp = self.client.get('/media/../etc/passwd')
        self.assertIn(resp.status_code, (403, 404))
