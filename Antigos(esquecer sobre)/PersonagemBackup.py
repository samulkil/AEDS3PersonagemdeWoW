import struct
import os

class Personagem:
    FORMATO = "1s i 20s f" # Lapide, ID, Nome, Nivel

    def __init__(self, id, nome, nivel, lapide=b' '):
        self.id = id
        # Garante que o nome seja bytes e tenha tamanho fixo
        if isinstance(nome, str):
            nome = nome.encode('utf-8')
        self.nome = nome[:20]
        self.nivel = nivel
        self.lapide = lapide

    def to_bytes(self):      
        nome_fixo = self.nome.ljust(20, b'\x00')
        return struct.pack(self.FORMATO, self.lapide, self.id, nome_fixo, self.nivel)
    
    @classmethod # OBRIGATÓRIO PARA USAR O 'cls'
    def from_bytes(cls, dados_binarios):
        lapide, id, nome, nivel = struct.unpack(cls.FORMATO, dados_binarios)
        return cls(id, nome.decode('utf-8').strip('\x00'), nivel, lapide)

class ArquivoPerso:
    def __init__(self, nome_arquivo="personagens.bin"):
        self.nome_arquivo = nome_arquivo
        self.formato_header = "i" 
        self.tamanho_header = struct.calcsize(self.formato_header)
        # Calculamos o tamanho do registro para facilitar o seek
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
            print(f"Personagem {novo_id} criado com sucesso!")

    def delete(self, id_alvo):

        with open(self.nome_arquivo, "rb+") as f: # r+ para poder alterar
            f.seek(self.tamanho_header)

            while True:
                posicao_da_lapide = f.tell() # Guarda onde o registro começa
                lapide = f.read(1)
                if not lapide:
                    print("ID não encontrado.")
                    break
                
                # Lê os dados para checar o ID
                dados = f.read(self.tamanho_registro - 1)
                id_lido = struct.unpack("i", dados[:4])[0]

                if lapide == b' ' and id_lido == id_alvo:
                    # Achou! Volta para a posição da lápide e grava o '*'
                    f.seek(posicao_da_lapide)
                    f.write(b'*') # EXCLUSÃO LÓGICA 
                    print(f"Personagem {id_alvo} excluído logicamente.")
                    return True
        return False
    
    def read(self,id_alvo):
        with open(self.nome_arquivo, "rb+") as f:
            f.seek(self.tamanho_header)
            while True:
                posicao_atual = f.tell()
                lapide = f.read(1)
                if not lapide:
                    #EOF
                    print("Existe não brow")
                    break
                dados = f.read(self.tamanho_registro - 1)
                id_lido = struct.unpack("i", dados[:4])[0]

                if(id_lido == id_alvo and lapide == b' '):
                    f.seek(posicao_atual)
                    registro_atual = f.read(self.tamanho_registro)
        return Personagem.from_bytes(registro_atual)
    
    def update(self, id_alvo, novo_nome, novo_nivel):
                with open(self.nome_arquivo, "rb+") as f:
                    f.seek(self.tamanho_header)
                    while True:
                        posicao_atual = f.tell()
                        lapide = f.read(1)
                        if not lapide:
                            print("Personagem nao existe")
                            break

                        dados = f.read(self.tamanho_registro - 1)
                        id_lido = struct.unpack("i",dados[:4])[0]

                        if(id_lido == id_alvo and lapide == b' '):
                            f.seek(posicao_atual)
                            PersoTemp = Personagem(id_alvo, novo_nome, novo_nivel, lapide=b' ')
                            dados = PersoTemp.to_bytes()
                            f.write(dados)
                            print(f"Personagem {id_alvo} atualizado com sucesso!")
                            return True 
                        




                
