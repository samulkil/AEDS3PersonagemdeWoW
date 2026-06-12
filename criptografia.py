"""
Módulo de criptografia XOR para senhas de usuário.

A operação XOR é simétrica: encrypt(decrypt(x)) == x
A chave é aplicada ciclicamente sobre os bytes do texto.
"""

CHAVE_XOR = b"WoWRPGcraft2024!"


def xor_cifrar(texto: str, chave: bytes = CHAVE_XOR) -> bytes:
    """Cifra um texto com XOR usando a chave fornecida."""
    dados = texto.encode("utf-8")
    return bytes(b ^ chave[i % len(chave)] for i, b in enumerate(dados))


def xor_decifrar(dados: bytes, chave: bytes = CHAVE_XOR) -> str:
    """Decifra bytes XOR de volta para texto."""
    # Remove bytes nulos de padding antes de decifrar
    dados = dados.rstrip(b"\x00")
    if not dados:
        return ""
    return bytes(b ^ chave[i % len(chave)] for i, b in enumerate(dados)).decode("utf-8")


def xor_verificar(texto: str, dados_cifrados: bytes, chave: bytes = CHAVE_XOR) -> bool:
    """Verifica se um texto corresponde aos dados cifrados."""
    return xor_cifrar(texto, chave) == dados_cifrados.rstrip(b"\x00")
