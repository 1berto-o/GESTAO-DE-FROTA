from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .validators import validar_matricula


Usuario = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Autenticação por matrícula + senha.
    Em primeiro acesso (precisa_definir_senha e senha ainda não definida),
    permite login apenas com a matrícula (senha vazia).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[self.username_field].required = True
        if 'password' in self.fields:
            self.fields['password'].required = False
            self.fields['password'].allow_blank = True

    def validate(self, attrs):
        matricula_bruta = attrs.get(self.username_field)
        password = attrs.get('password') or ''

        try:
            matricula = validar_matricula(matricula_bruta)
        except DjangoValidationError:
            raise self._auth_error()

        attrs[self.username_field] = matricula

        try:
            user = Usuario.objects.get(**{self.username_field: matricula})
        except Usuario.DoesNotExist:
            raise self._auth_error()

        if user.precisa_definir_senha and not user.has_usable_password():
            if password:
                raise self._auth_error()
        elif not user.check_password(password):
            raise self._auth_error()

        refresh = self.get_token(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'precisa_definir_senha': bool(user.precisa_definir_senha),
            'is_admin': bool(user.is_admin),
            'matricula': user.matricula,
            'nome': user.nome,
        }

    def _auth_error(self):
        return serializers.ValidationError(
            'Usuário ou senha inválidos.',
            code='authorization',
        )


def user_authentication_rule(user):
    """Aceita usuário autenticado mesmo se is_active=False."""
    return user is not None


class DefinirSenhaSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': ['A confirmação não confere com a senha.'],
            })
        validate_password(attrs['password'], user=self.context['request'].user)
        return attrs

    def save(self, **kwargs):
        user = self.context['request'].user
        user.definir_senha(self.validated_data['password'])
        return user


class SolicitarRecuperacaoSenhaSerializer(serializers.Serializer):
    matricula = serializers.CharField(max_length=50)

    def validate_matricula(self, value):
        try:
            return validar_matricula(value)
        except DjangoValidationError as exc:
            # Anti-enumeração: formato inválido não revela regra distinta
            # no endpoint público — a view ainda responde 200 genérico se
            # preferirmos; aqui rejeitamos com mensagem clara de formato.
            raise serializers.ValidationError(exc.messages)


class RedefinirSenhaCodigoSerializer(serializers.Serializer):
    matricula = serializers.CharField(max_length=50)
    codigo = serializers.CharField(max_length=32)
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    def validate_matricula(self, value):
        try:
            return validar_matricula(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': ['A confirmação não confere com a senha.'],
            })
        matricula = attrs.get('matricula') or ''
        user = Usuario.objects.filter(matricula=matricula).first()
        if user:
            validate_password(attrs['password'], user=user)
        else:
            validate_password(attrs['password'])
        return attrs


class RejeitarRecuperacaoSerializer(serializers.Serializer):
    observacao = serializers.CharField(required=False, allow_blank=True, max_length=255)
