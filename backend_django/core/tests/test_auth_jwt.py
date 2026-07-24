"""El token es la base del aislamiento entre tenants: se prueba a conciencia."""
from django.test import TestCase

from core.auth_jwt import TokenError, decode_token, issue_token
from core.models import Tenant, User


class TokenTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug="acme", name="Acme SA")
        self.agent = User.objects.create_user(
            username="agente_acme", password="x", tenant=self.tenant, is_support_agent=True
        )

    def test_el_token_lleva_el_tenant_firmado(self):
        token, expires_in = issue_token(self.agent)
        claims = decode_token(token)

        self.assertEqual(claims.user_id, self.agent.pk)
        self.assertEqual(claims.tenant_id, self.tenant.pk)
        self.assertEqual(claims.tenant_slug, "acme")
        self.assertTrue(claims.is_support_agent)
        self.assertGreater(expires_in, 0)

    def test_un_token_manipulado_se_rechaza(self):
        token, _ = issue_token(self.agent)
        header, payload, signature = token.split(".")
        alterado = f"{header}.{payload}.{signature[:-4]}xxxx"

        with self.assertRaises(TokenError):
            decode_token(alterado)

    def test_usuario_sin_tenant_produce_tenant_nulo(self):
        admin = User.objects.create_superuser(username="admin", password="x")
        claims = decode_token(issue_token(admin)[0])

        self.assertIsNone(claims.tenant_id)
        self.assertIsNone(claims.tenant_slug)
        self.assertTrue(claims.is_staff)
