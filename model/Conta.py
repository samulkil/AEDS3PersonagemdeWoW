import struct

class Conta:
    # Formato: Lápide(1s), ID(i), Usuário(20s), Email(30s), Data(10s)
    # Total fixo: 65 bytes
    FORMATO = "<1s i 20s 30s 10s" 

    def __init__(self, id, usuario, email, data, lapide=b' '):
        self.id = id
        # Tratamento para garantir tamanhos fixos
        self.usuario = usuario.encode('utf-8')[:20] if isinstance(usuario, str) else usuario[:20]
        self.email = email.encode('utf-8')[:30] if isinstance(email, str) else email[:30]
        self.data = data.encode('utf-8')[:10] if isinstance(data, str) else data[:10]
        self.lapide = lapide

    def to_bytes(self):      
        u_fixo = self.usuario.ljust(20, b'\x00')
        e_fixo = self.email.ljust(30, b'\x00')
        d_fixo = self.data.ljust(10, b'\x00')
        return struct.pack(self.FORMATO, self.lapide, self.id, u_fixo, e_fixo, d_fixo)
    
    @classmethod 
    def from_bytes(cls, dados_binarios):
        lapide, id, usuario, email, data = struct.unpack(cls.FORMATO, dados_binarios)
        return cls(
            id, 
            usuario.decode('utf-8').strip('\x00'), 
            email.decode('utf-8').strip('\x00'), 
            data.decode('utf-8').strip('\x00'), 
            lapide
        )