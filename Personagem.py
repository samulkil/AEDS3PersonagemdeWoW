import struct
import os

class Personagem:
    # FORMATO: 1s (Lápide), i (ID), 20s (Nome), f (Nível), i (ID_Conta - FK)
    FORMATO = "<1s i 20s f i" 

    def __init__(self, id, nome, nivel, id_conta, lapide=b' '):
        self.id = id
        if isinstance(nome, str):
            nome = nome.encode('utf-8')
        self.nome = nome[:20]
        self.nivel = nivel
        self.id_conta = id_conta # Chave Estrangeira para a Conta
        self.lapide = lapide

    def to_bytes(self):      
        nome_fixo = self.nome.ljust(20, b'\x00')
        return struct.pack(self.FORMATO, self.lapide, self.id, nome_fixo, self.nivel, self.id_conta)
    
    @classmethod 
    def from_bytes(cls, dados_binarios):
        lapide, id, nome, nivel, id_conta = struct.unpack(cls.FORMATO, dados_binarios)
        return cls(id, nome.decode('utf-8').strip('\x00'), nivel, id_conta, lapide)

class ArquivoPerso:
    def __init__(self, nome_arquivo="personagens.bin"):
        self.nome_arquivo = nome_arquivo
        self.formato_header = "i" 
        self.tamanho_header = struct.calcsize(self.formato_header)
        self.tamanho_registro = struct.calcsize(Personagem.FORMATO)
        
        if not os.path.exists(self.nome_arquivo):
            with open(self.nome_arquivo, "wb") as f:
                f.write(struct.pack(self.formato_header, 0))
    
    def create(self, personagem):
        with open(self.nome_arquivo, "rb+") as f:
            f.seek(0)
            ultimo_id = struct.unpack(self.formato_header, f.read(self.tamanho_header))[0]
            novo_id = ultimo_id + 1
            personagem.id = novo_id
            
            f.seek(0, 2)
            f.write(personagem.to_bytes())

            f.seek(0)
            f.write(struct.pack(self.formato_header, novo_id))
            print(f"Personagem {novo_id} criado e vinculado à conta {personagem.id_conta}!")

    def read(self, id_alvo):
        with open(self.nome_arquivo, "rb") as f:
            f.seek(self.tamanho_header)
            while True:
                posicao_atual = f.tell()
                lapide = f.read(1)
                if not lapide: break
            
                dados_restantes = f.read(self.tamanho_registro - 1)
                # Use o prefixo '<' aqui também!
                id_lido = struct.unpack("<i", dados_restantes[:4])[0]

                if id_lido == id_alvo and lapide == b' ':
                    f.seek(posicao_atual)
                    return Personagem.from_bytes(f.read(self.tamanho_registro))
        return None

    def update(self, id_alvo, novo_nome, novo_nivel, novo_id_conta):
        with open(self.nome_arquivo, "rb+") as f:
            f.seek(self.tamanho_header)
            while True:
                posicao_atual = f.tell()
                lapide = f.read(1)
                if not lapide:
                    print("Personagem nao existe")
                    break

                dados = f.read(self.tamanho_registro - 1)
                id_lido = struct.unpack("i", dados[:4])[0]

                if id_lido == id_alvo and lapide == b' ':
                    f.seek(posicao_atual)
                    perso_atualizado = Personagem(id_alvo, novo_nome, novo_nivel, novo_id_conta)
                    f.write(perso_atualizado.to_bytes())
                    print(f"Personagem {id_alvo} atualizado com sucesso!")
                    return True 
        return False

    def delete(self, id_alvo):
        with open(self.nome_arquivo, "rb+") as f:
            f.seek(self.tamanho_header)
            while True:
                posicao_da_lapide = f.tell()
                lapide = f.read(1)
                if not lapide:
                    break
                
                dados = f.read(self.tamanho_registro - 1)
                id_lido = struct.unpack("i", dados[:4])[0]

                if lapide == b' ' and id_lido == id_alvo:
                    f.seek(posicao_da_lapide)
                    f.write(b'*') # Exclusão lógica
                    return True
        return False
    
    def listar_por_conta(self, id_conta_alvo):
        """Lista todos os personagens que pertencem a uma conta específica"""
        encontrou = False
        with open(self.nome_arquivo, "rb") as f:
            f.seek(self.tamanho_header)
            print(f"\n{'ID':<5} | {'NOME':<20} | {'NÍVEL':<10}")
            print("-" * 40)
            
            while True:
                posicao_atual = f.tell()
                lapide = f.read(1)
                if not lapide:
                    break
                
                dados = f.read(self.tamanho_registro - 1)
                # Desempacotamos tudo para conferir a FK (id_conta)
                # Seguindo o formato: <1s i 20s f i
                _, id_perso, nome, nivel, id_c = struct.unpack("<1s i 20s f i", lapide + dados)
                
                if lapide == b' ' and id_c == id_conta_alvo:
                    nome_limpo = nome.decode('utf-8').strip('\x00')
                    print(f"{id_perso:<5} | {nome_limpo:<20} | {nivel:<10.2f}")
                    encontrou = True
        
        if not encontrou:
            print("Nenhum personagem encontrado para esta conta.")