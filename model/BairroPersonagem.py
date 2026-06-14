import struct

class BairroPersonagem:
    FORMATO = "<1s i i q"

    def __init__(self, id_bairro, id_personagem, prox=-1, lapide=b' '):
        self.id_bairro = id_bairro
        self.id_personagem = id_personagem
        self.lapide = lapide
        self.prox = prox

    def to_bytes(self):
        return struct.pack(self.FORMATO, self.lapide, self.id_bairro, self.id_personagem, self.prox)

    @classmethod
    def from_bytes(cls, dados):
        lapide, id_bairro, id_personagem, prox = struct.unpack(cls.FORMATO, dados)
        return cls(id_bairro, id_personagem, prox, lapide)

    def __str__(self):
        return f"BairroPersonagem(Bairro: {self.id_bairro}, Personagem: {self.id_personagem})"
