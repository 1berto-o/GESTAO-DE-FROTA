"""
URL configuration for FleetOps.
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings

from .media_access import ProtectedMediaView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/usuarios/', include('usuarios.urls')),
    path('api/veiculos/', include('veiculos.urls')),
    path('api/reservas/', include('reservas.urls')),
    path('api/vistorias/', include('vistorias.urls')),
    path('api/termos/', include('termos.urls')),
    path('api/auditoria/', include('auditoria.urls')),
    path('api/relatorios/', include('relatorios.urls')),
]

# Storage local: /media/ passa pelo Django (auth / token assinado).
# Com Supabase Storage as URLs apontam para o bucket e esta rota não é usada.
if not getattr(settings, 'USE_SUPABASE_STORAGE', False):
    urlpatterns += [
        re_path(
            r'^media/(?P<path>.*)$',
            ProtectedMediaView.as_view(),
            name='media-protegida',
        ),
    ]
