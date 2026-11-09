# Backend — FleetOps

API Django REST Framework do FleetOps.

```bash
python manage.py migrate
python manage.py criar_admin_inicial --matricula 000001 --nome Admin --password 'SENHA_FORTE'
python manage.py test --settings=config.test_settings
```

Documentação: [../docs/desenvolvimento/api.md](../docs/desenvolvimento/api.md).

Documentação: [docs/](../docs/) — [instalação](../docs/operacao/implantacao.md), [API](../docs/desenvolvimento/api.md), [desenvolvimento](../docs/desenvolvimento/guia-desenvolvimento.md).

## Comandos frequentes

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
python manage.py check
```

Para Docker no Debian use o `.env` da **raiz** do projeto (`../.env.example`), não este arquivo como `.env` do Compose.
