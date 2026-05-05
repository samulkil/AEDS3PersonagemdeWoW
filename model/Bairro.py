import struct

class Bairro:
    # Formato: Lápide(1s), ID(i), Nome(30s), ID_Dono(i), Próximo(q)
    # Total fixo: 48 bytes (1 + 4 + 30 + 4 + 8)
    FORMATO = "<1s i 30s i q" 

    def __init__(self, id, nome, id_dono, prox=-1, lapide=b' '):
        self.id = id
        # Garante tamanho fixo de 30 bytes para o nome
        self.nome = nome.encode('utf-8')[:30] if isinstance(nome, str) else nome[:30]
        self.id_dono = id_dono  # ID do Personagem que é o dono do bairro
        self.lapide = lapide
        self.prox = prox  # Ponteiro para o relacionamento N:N com personagens

    def to_bytes(self):      
        """Converte o objeto para bytes para gravação em arquivo binário."""
        nome_f = self.nome.ljust(30, b'\x00')
        return struct.pack(
            self.FORMATO, 
            self.lapide, 
            self.id, 
            nome_f, 
            self.id_dono, 
            self.prox
        )
    
    @classmethod 
    def from_bytes(cls, dados):
        """Reconstrói o objeto a partir de dados binários lidos do disco."""
        lapide, id, nome, id_dono, prox = struct.unpack(cls.FORMATO, dados)
        return cls(
            id, 
            nome.decode('utf-8').strip('\x00'), 
            id_dono, 
            prox, 
            lapide
        )

    def __str__(self):
        return f"Bairro(ID: {self.id}, Nome: {self.nome.decode('utf-8').strip(chr(0))}, Dono: {self.id_dono})"
