import struct

class BairroPersonagem:
    # Formato para o relacionamento N:N: Lápide(1s), ID_Bairro(i), ID_Personagem(i), Próximo(q)
    # Total fixo: 18 bytes (1 + 4 + 4 + 8 + 1 de padding)
    FORMATO = "<1s i i q" 

    def __init__(self, id_bairro, id_personagem, prox=-1, lapide=b' '):
        self.id_bairro = id_bairro
        self.id_personagem = id_personagem
        self.lapide = lapide
        self.prox = prox  # Ponteiro para o próximo registro na lista encadeada

    def to_bytes(self):      
        """Converte o objeto para bytes para gravação em arquivo binário."""
        return struct.pack(
            self.FORMATO, 
            self.lapide, 
            self.id_bairro, 
            self.id_personagem, 
            self.prox
        )
    
    @classmethod 
    def from_bytes(cls, dados):
        """Reconstrói o objeto a partir de dados binários lidos do disco."""
        lapide, id_bairro, id_personagem, prox = struct.unpack(cls.FORMATO, dados)
        return cls(id_bairro, id_personagem, prox, lapide)

    def __str__(self):
        return f"BairroPersonagem(Bairro: {self.id_bairro}, Personagem: {self.id_personagem})"
