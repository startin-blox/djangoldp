from Cryptodome.PublicKey import RSA
from django.db import IntegrityError
from django.test import TestCase
from djangoldp_crypto.models import RSAKey


class TestRSAKey(TestCase):
    def test_rsakey_unique(self):
        priv_key = RSA.generate(2048)
        RSAKey.objects.create(priv_key=priv_key)
        with self.assertRaises(IntegrityError):
            RSAKey.objects.create(priv_key=priv_key)
