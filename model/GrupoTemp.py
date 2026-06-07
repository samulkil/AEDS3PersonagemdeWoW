import struct
import os

class GrupoTemp:
    FORMATO = "<1s i i i" 

    def __init__(self, id_grupo, id_conta, id_personagem, lapide=b' '):
        self.id_grupo = id_grupo
        self.id_conta = id_conta
        self.id_personagem = id_personagem
        self.lapide = lapide
    
    def to_bytes(self):
        return struct.pack(self.FORMATO, self.lapide, self.id_grupo, self.id_conta, self.id_personagem)
    
    @classmethod
    def from_bytes(cls, dados_binarios):
        lapide, id_g, id_c, id_p = struct.unpack(cls.FORMATO, dados_binarios)
        return cls(id_g, id_c, id_p, lapide)