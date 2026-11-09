from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    CustomTokenObtainPairView, PerfilView, DefinirSenhaView,
    RedefinirSenhaAdminView,
    SolicitarRecuperacaoSenhaView,
    RecuperacaoSenhaAdminListView,
    AprovarRecuperacaoSenhaView,
    RejeitarRecuperacaoSenhaView,
    RedefinirSenhaComCodigoView,
    UsuarioListCreateView, UsuarioDetailView,
    SetorListCreateView, SetorDetailView,
    SetorUsuariosView, SetorTransferenciaView,
    MeuStatusCNHView, DocumentoCNHListCreateView,
    DocumentoCNHDecisaoView, documento_cnh_detail, PendenciasAdminView,
)

urlpatterns = [
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('definir-senha/', DefinirSenhaView.as_view(), name='definir-senha'),
    path('perfil/', PerfilView.as_view(), name='perfil'),
    path('pendencias/', PendenciasAdminView.as_view(), name='pendencias-admin'),
    path('setores/', SetorListCreateView.as_view(), name='setor-list-create'),
    path('setores/<int:pk>/', SetorDetailView.as_view(), name='setor-detail'),
    path(
        'setores/<int:pk>/usuarios/',
        SetorUsuariosView.as_view(),
        name='setor-usuarios',
    ),
    path(
        'setores/<int:pk>/transferir/',
        SetorTransferenciaView.as_view(),
        name='setor-transferir',
    ),
    path(
        'recuperacao-senha/solicitar/',
        SolicitarRecuperacaoSenhaView.as_view(),
        name='recuperacao-solicitar',
    ),
    path(
        'recuperacao-senha/redefinir/',
        RedefinirSenhaComCodigoView.as_view(),
        name='recuperacao-redefinir',
    ),
    path(
        'recuperacao-senha/',
        RecuperacaoSenhaAdminListView.as_view(),
        name='recuperacao-list',
    ),
    path(
        'recuperacao-senha/<int:pk>/aprovar/',
        AprovarRecuperacaoSenhaView.as_view(),
        name='recuperacao-aprovar',
    ),
    path(
        'recuperacao-senha/<int:pk>/rejeitar/',
        RejeitarRecuperacaoSenhaView.as_view(),
        name='recuperacao-rejeitar',
    ),
    path('cnh/meu-status/', MeuStatusCNHView.as_view(), name='cnh-meu-status'),
    path('cnh/', DocumentoCNHListCreateView.as_view(), name='cnh-list-create'),
    path('cnh/<int:pk>/', documento_cnh_detail, name='cnh-detail'),
    path('cnh/<int:pk>/decisao/', DocumentoCNHDecisaoView.as_view(), name='cnh-decisao'),
    path('', UsuarioListCreateView.as_view(), name='usuario-list-create'),
    path('<int:pk>/redefinir-senha/', RedefinirSenhaAdminView.as_view(), name='usuario-redefinir-senha'),
    path('<int:pk>/', UsuarioDetailView.as_view(), name='usuario-detail'),
]
