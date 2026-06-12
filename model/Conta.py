import struct
from criptografia import xor_cifrar, xor_decifrar, xor_verificar

class Conta:
    # Formato: Lápide(1s), ID(i), Usuário(20s), Email(30s), Data(10s), Senha_XOR(20s)
    # Total fixo: 85 bytes
    FORMATO = "<1s i 20s 30s 10s 20s"

    def __init__(self, id, usuario, email, data, lapide=b' ', senha_cifrada=b''):
        self.id = id
        self.usuario = usuario.encode('utf-8')[:20] if isinstance(usuario, str) else usuario[:20]
        self.email = email.encode('utf-8')[:30] if isinstance(email, str) else email[:30]
        self.data = data.encode('utf-8')[:10] if isinstance(data, str) else data[:10]
        self.lapide = lapide
        # Armazena os bytes cifrados diretamente
        self.senha_cifrada = senha_cifrada[:20] if isinstance(senha_cifrada, bytes) else b''

    def set_senha(self, senha_texto: str):
        """Cifra e armazena a senha usando XOR."""
        self.senha_cifrada = xor_cifrar(senha_texto[:20])

    def verificar_senha(self, senha_texto: str) -> bool:
        """Verifica se a senha fornecida corresponde à senha cifrada."""
        return xor_verificar(senha_texto, self.senha_cifrada)

    def to_bytes(self):
        u_fixo = self.usuario.ljust(20, b'\x00')
        e_fixo = self.email.ljust(30, b'\x00')
        d_fixo = self.data.ljust(10, b'\x00')
        s_fixo = self.senha_cifrada.ljust(20, b'\x00')
        return struct.pack(self.FORMATO, self.lapide, self.id, u_fixo, e_fixo, d_fixo, s_fixo)

    @classmethod
    def from_bytes(cls, dados_binarios):
        lapide, id, usuario, email, data, senha_cifrada = struct.unpack(cls.FORMATO, dados_binarios)
        return cls(
            id,
            usuario.decode('utf-8').strip('\x00'),
            email.decode('utf-8').strip('\x00'),
            data.decode('utf-8').strip('\x00'),
            lapide,
            senha_cifrada,
        )