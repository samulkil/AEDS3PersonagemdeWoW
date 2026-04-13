import os
import struct
from model.Personagem import Personagem
from model.ArvoreBPlus import ArvoreBPlus

class PersonagemDAO:
    def __init__(self, arquivo="dados/personagens.bin"):
        self.arquivo = arquivo
        self.header_fmt = "<i"
        self.header_size = struct.calcsize(self.header_fmt)
        self.reg_size = struct.calcsize(Personagem.FORMATO)
        
        self.arvore_id = ArvoreBPlus("dados/index_id.bin", ordem=4)
        self.arvore_nivel = ArvoreBPlus("dados/index_nivel.bin", ordem=4)
        self.reconstruir_indice()
        
        
        if not os.path.exists(self.arquivo):
            os.makedirs(os.path.dirname(self.arquivo), exist_ok=True)
            with open(self.arquivo, "wb") as f:
                f.write(struct.pack(self.header_fmt, 0))

    def create(self, personagem):
        with open(self.arquivo, "rb+") as f:
            f.seek(0)
            ultimo_id = struct.unpack(self.header_fmt, f.read(self.header_size))[0]
            novo_id = ultimo_id + 1
            personagem.id = novo_id
            
            f.seek(0, 2)
            pos = f.tell()  

            f.write(personagem.to_bytes())

            # índice por ID
            self.arvore_id.inserir(novo_id, pos)

            # índice por nível 
            nivel_int = int(personagem.nivel)
            self.arvore_nivel.inserir(nivel_int, pos)

            f.seek(0)
            f.write(struct.pack(self.header_fmt, novo_id))

        print(f"Personagem {novo_id} criado!")
        
    def read(self, id_alvo):
        with open(self.arquivo, "rb") as f:
            f.seek(self.header_size)
            while True:
                posicao_atual = f.tell()
                lapide = f.read(1)
                if not lapide: break
            
                dados_restantes = f.read(self.reg_size - 1)
                id_lido = struct.unpack("<i", dados_restantes[:4])[0]

                if id_lido == id_alvo and lapide == b' ':
                    f.seek(posicao_atual)
                    return Personagem.from_bytes(f.read(self.reg_size))
        return None
    
    #leitura da B+
    def read_bplus(self, id_alvo):
        pos = self.arvore.buscar(id_alvo)

        if pos is None:
            return None

        with open(self.arquivo, "rb") as f:
            f.seek(pos)
            dados = f.read(self.reg_size)

            lapide = dados[0:1]

            if lapide != b' ':
                return None

            return Personagem.from_bytes(dados)

    def listar_por_conta(self, id_conta_alvo):
        encontrou = False
        with open(self.arquivo, "rb") as f:
            f.seek(self.header_size) # Pula o cabeçalho de 4 bytes
            while True:
                # Lê o registro COMPLETO (33 bytes: 1+4+20+4+4)
                dados = f.read(self.reg_size) 
                if not dados: break
                
                # Desempacota os 5 campos
                lapide, id_perso, nome, nivel, id_c = struct.unpack("<1s i 20s f i", dados)
                
                if lapide == b' ' and id_c == id_conta_alvo:
                    nome_limpo = nome.decode('utf-8').strip('\x00')
                    print(f"{id_perso:<5} | {nome_limpo:<20} | {nivel:<10.2f}")
                    encontrou = True

    def delete(self, id_alvo):
        with open(self.arquivo, "rb+") as f:
            f.seek(self.header_size)
            while True:
                posicao_da_lapide = f.tell()
                lapide = f.read(1)
                if not lapide:
                    break
                
                dados = f.read(self.reg_size - 1)
                id_lido = struct.unpack("<i", dados[:4])[0]

                if lapide == b' ' and id_lido == id_alvo:
                    f.seek(posicao_da_lapide)
                    f.write(b'*') # Exclusão lógica
                    return True
        return False
    
    def update(self, id_alvo, novo_nome, novo_nivel, novo_id_conta):
        with open(self.arquivo, "rb+") as f:
            f.seek(self.header_size)
            while True:
                posicao_atual = f.tell()
                lapide = f.read(1)
                if not lapide:
                    print("Personagem nao existe")
                    break

                dados = f.read(self.reg_size - 1)
                id_lido = struct.unpack("<i", dados[:4])[0]

                if id_lido == id_alvo and lapide == b' ':
                    f.seek(posicao_atual)
                    perso_atualizado = Personagem(id_alvo, novo_nome, novo_nivel, novo_id_conta)
                    f.write(perso_atualizado.to_bytes())
                    print(f"Personagem {id_alvo} atualizado com sucesso!")
                    return True 
        return False
    
    def buscar_por_nivel(self, nivel):
        posicoes = self.arvore_nivel.buscar_todos(int(nivel))

        personagens = []

        with open(self.arquivo, "rb") as f:
            for pos in posicoes:
                f.seek(pos)
                dados = f.read(self.reg_size)

                if dados[0:1] == b' ':
                    personagens.append(Personagem.from_bytes(dados))

        return personagens
    
    #Sempre roda, mas o melhor e rodar uma vez para sincronizar a arvore com os dados antigos 
    def reconstruir_indice(self):
        print("Reconstruindo índice B+...")

        # apaga índice antigo
        if os.path.exists("dados/index_personagem.bin"):
            os.remove("dados/index_personagem.bin")

        self.arvore = ArvoreBPlus("dados/index_personagem.bin", ordem=4)

        with open(self.arquivo, "rb") as f:
            f.seek(self.header_size)

            while True:
                pos = f.tell()
                dados = f.read(self.reg_size)

                if not dados:
                    break

                lapide = dados[0:1]
                id_lido = struct.unpack("<i", dados[1:5])[0]

                if lapide == b' ':
                    self.arvore.inserir(id_lido, pos)

        print("Índice reconstruído com sucesso!")