import struct

class Personagem:

    FORMATO = "<1s i 20s f i" 

    def __init__(self, id, nome, nivel, id_conta, lapide=b' '):
        self.id = id
        self.nome = nome.encode('utf-8')[:20] if isinstance(nome, str) else nome[:20]
        self.nivel = nivel
        self.id_conta = id_conta 
        self.lapide = lapide

    def to_bytes(self):      
        nome_f = self.nome.ljust(20, b'\x00')
        return struct.pack(self.FORMATO, self.lapide, self.id, nome_f, self.nivel, self.id_conta)
    
    @classmethod 
    def from_bytes(cls, dados):
        lapide, id, nome, nivel, id_c = struct.unpack(cls.FORMATO, dados)
        return cls(id, nome.decode('utf-8').strip('\x00'), nivel, id_c, lapide)