"""Tests for n_2_encrypted_browser_server_communication (CryptIO RSA-OAEP nodes)."""

import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from n_2_encrypted_browser_server_communication import (
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    PSN_CryptIO_Decrypt,
    PSN_CryptIO_Encrypt,
)


def _make_keys(bits=2048):
    priv = rsa.generate_private_key(public_exponent=65537, key_size=bits)
    pub_pem = priv.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    priv_pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    return pub_pem, priv_pem


def test_module_mappings():
    assert "PSN_CryptIO_Encrypt" in NODE_CLASS_MAPPINGS
    assert "PSN_CryptIO_Decrypt" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_CryptIO_Encrypt"] is PSN_CryptIO_Encrypt
    assert NODE_CLASS_MAPPINGS["PSN_CryptIO_Decrypt"] is PSN_CryptIO_Decrypt
    assert "PSN_CryptIO_Encrypt" in NODE_DISPLAY_NAME_MAPPINGS
    assert "PSN_CryptIO_Decrypt" in NODE_DISPLAY_NAME_MAPPINGS


def test_input_types_contract():
    for cls in (PSN_CryptIO_Encrypt, PSN_CryptIO_Decrypt):
        spec = cls.INPUT_TYPES()
        assert "required" in spec
        assert cls.FUNCTION == "run"
        assert cls.CATEGORY.startswith("ParametricStudio/")
        assert isinstance(cls.RETURN_TYPES, tuple)
        assert isinstance(cls.RETURN_NAMES, tuple)
        assert len(cls.RETURN_TYPES) == len(cls.RETURN_NAMES)


def test_roundtrip_short():
    pub, priv = _make_keys()
    enc = PSN_CryptIO_Encrypt().run("hello world", pub)[0]
    # Output must be valid Base64 (single chunk -> one line)
    raw = base64.b64decode(enc, validate=True)
    assert len(raw) == 256  # RSA-2048 ciphertext length
    dec = PSN_CryptIO_Decrypt().run(enc, priv)[0]
    assert dec == "hello world"


def test_roundtrip_long_multichunk():
    pub, priv = _make_keys()
    msg = "A" * 500 + "-" + "B" * 300  # 801 chars -> multiple 190-byte chunks
    enc = PSN_CryptIO_Encrypt().run(msg, pub)[0]
    lines = [l for l in enc.split("\n") if l.strip()]
    assert len(lines) >= 5  # 801/190 = 5 chunks
    for l in lines:
        assert len(base64.b64decode(l, validate=True)) == 256
    dec = PSN_CryptIO_Decrypt().run(enc, priv)[0]
    assert dec == msg


def test_unicode_roundtrip():
    pub, priv = _make_keys()
    msg = "héllo wörld — 日本語 🚀"
    enc = PSN_CryptIO_Encrypt().run(msg, pub)[0]
    dec = PSN_CryptIO_Decrypt().run(enc, priv)[0]
    assert dec == msg


def test_encrypt_empty_data_raises():
    pub, _ = _make_keys()
    try:
        PSN_CryptIO_Encrypt().run("", pub)
        assert False, "expected ValueError for empty data"
    except ValueError:
        pass


def test_encrypt_bad_public_key_raises():
    try:
        PSN_CryptIO_Encrypt().run("data", "not-a-pem")
        assert False, "expected error for bad public key"
    except Exception:
        pass


def test_decrypt_bad_base64_raises():
    _, priv = _make_keys()
    try:
        PSN_CryptIO_Decrypt().run("!!!not-base64!!!", priv)
        assert False, "expected ValueError for bad base64"
    except ValueError:
        pass


def test_decrypt_wrong_key_raises():
    pub1, _ = _make_keys()
    _, priv2 = _make_keys()
    enc = PSN_CryptIO_Encrypt().run("secret", pub1)[0]
    try:
        PSN_CryptIO_Decrypt().run(enc, priv2)
        assert False, "expected decryption failure with wrong key"
    except Exception:
        pass


def test_non_string_input_raises():
    pub, priv = _make_keys()
    try:
        PSN_CryptIO_Encrypt().run(12345, pub)
        assert False, "expected ValueError for non-string data"
    except ValueError:
        pass
    try:
        PSN_CryptIO_Decrypt().run(None, priv)
        assert False, "expected ValueError for non-string encrypted_data"
    except ValueError:
        pass


def main():
    test_module_mappings()
    test_input_types_contract()
    test_roundtrip_short()
    test_roundtrip_long_multichunk()
    test_unicode_roundtrip()
    test_encrypt_empty_data_raises()
    test_encrypt_bad_public_key_raises()
    test_decrypt_bad_base64_raises()
    test_decrypt_wrong_key_raises()
    test_non_string_input_raises()
    print("ok")


if __name__ == "__main__":
    main()
