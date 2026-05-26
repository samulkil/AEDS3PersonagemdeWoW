import struct

class Bairro:
    FORMATO = "<1s i 30s i q" 

    def __init__(self, id, nome, id_dono, lapide=b' '):
        self.id = id
        self.nome = nome.encode('utf-8')[:30] if isinstance(nome, str) else nome[:30]
        self.id_dono = id_dono
        self.lapide = lapide

    def to_bytes(self):      
        """Converte o objeto para bytes para gravaÃ§Ã£o em arquivo binÃ¡rio."""
        nome_f = self.nome.ljust(30, b'\x00')
        reservado = 0
        return struct.pack(
            self.FORMATO, 
            self.lapide, 
            self.id, 
            nome_f, 
            self.id_dono, 
            reservado
        )
    
    @classmethod 
    def from_bytes(cls, dados):
        """ReconstrÃ³i o objeto a partir de dados binÃ¡rios lidos do disco."""
        lapide, id, nome, id_dono, _reservado = struct.unpack(cls.FORMATO, dados)
        return cls(
            id, 
            nome.decode('utf-8').strip('\x00'), 
            id_dono, 
            lapide
        )

    def __str__(self):
        return f"Bairro(ID: {self.id}, Nome: {self.nome.decode('utf-8').strip(chr(0))}, Dono: {self.id_dono})"
