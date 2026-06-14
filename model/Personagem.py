import struct

class Personagem:
    FORMATO = "<1s i 20s f i 10s q"

    def __init__(self, id, nome, nivel, id_conta, funcao="dano", prox=-1, lapide=b' '):
        self.id = id
        self.nome = nome.encode('utf-8')[:20] if isinstance(nome, str) else nome[:20]
        self.nivel = nivel
        self.id_conta = id_conta
        self.lapide = lapide
        self.prox = prox
        funcoes_validas = ["dano", "tanque", "suporte"]
        if isinstance(funcao, bytes):
            funcao = funcao.decode('utf-8').strip('\x00')
        if funcao.lower() not in funcoes_validas:
            raise ValueError("Função inválida! Escolha entre: dano, tanque ou suporte.")
        self.funcao = funcao.lower().encode('utf-8')[:10]

    def to_bytes(self):
        nome_f = self.nome.ljust(20, b'\x00')
        funcao_f = self.funcao.ljust(10, b'\x00')
        return struct.pack(self.FORMATO, self.lapide, self.id, nome_f, self.nivel, self.id_conta, funcao_f, self.prox)

    @classmethod
    def from_bytes(cls, dados):
        lapide, id, nome, nivel, id_c, funcao, prox = struct.unpack(cls.FORMATO, dados)
        return cls(
            id,
            nome.decode('utf-8').strip('\x00'),
            nivel,
            id_c,
            funcao.decode('utf-8').strip('\x00'),
            prox,
            lapide
        )
