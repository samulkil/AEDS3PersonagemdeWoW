import struct

class Personagem:
    # Formato: Lápide(1s), ID(i), Nome(20s), Nível(f), ID_Conta(i), Função(10s), Próximo(q)
    # Total fixo: 51 bytes (1 + 4 + 20 + 4 + 4 + 10 + 8)
    FORMATO = "<1s i 20s f i 10s q" 

    def __init__(self, id, nome, nivel, id_conta, funcao="dano", prox=-1, lapide=b' '):
        self.id = id
        # Garante tamanho fixo de 20 bytes para o nome
        self.nome = nome.encode('utf-8')[:20] if isinstance(nome, str) else nome[:20]
        self.nivel = nivel
        self.id_conta = id_conta 
        self.lapide = lapide
        self.prox = prox # Ponteiro para a lista encadeada do relacionamento 1:N
        
        # Validação da função (Requisito de Atributo Específico)
        funcoes_validas = ["dano", "tanque", "suporte"]
        if isinstance(funcao, bytes):
            funcao = funcao.decode('utf-8').strip('\x00')
            
        if funcao.lower() not in funcoes_validas:
            raise ValueError("Função inválida! Escolha entre: dano, tanque ou suporte.")
        self.funcao = funcao.lower().encode('utf-8')[:10]

    def to_bytes(self):      
        """Converte o objeto para bytes para gravação em arquivo binário."""
        nome_f = self.nome.ljust(20, b'\x00')
        funcao_f = self.funcao.ljust(10, b'\x00')
        # CORREÇÃO: Agora enviamos os 7 itens exigidos pelo FORMATO
        return struct.pack(
            self.FORMATO, 
            self.lapide, 
            self.id, 
            nome_f, 
            self.nivel, 
            self.id_conta, 
            funcao_f, 
            self.prox
        )
    
    @classmethod 
    def from_bytes(cls, dados):
        """Reconstrói o objeto a partir de dados binários lidos do disco."""
        # Desempacota os 7 campos conforme o FORMATO atualizado
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