CHAVE_XOR = b"WoWRPGcraft2024!"


def xor_cifrar(texto: str, chave: bytes = CHAVE_XOR) -> bytes:
    dados = texto.encode("utf-8")
    return bytes(b ^ chave[i % len(chave)] for i, b in enumerate(dados))


def xor_decifrar(dados: bytes, chave: bytes = CHAVE_XOR) -> str:
    dados = dados.rstrip(b"\x00")
    if not dados:
        return ""
    return bytes(b ^ chave[i % len(chave)] for i, b in enumerate(dados)).decode("utf-8")


def xor_verificar(texto: str, dados_cifrados: bytes, chave: bytes = CHAVE_XOR) -> bool:
    return xor_cifrar(texto, chave) == dados_cifrados.rstrip(b"\x00")
