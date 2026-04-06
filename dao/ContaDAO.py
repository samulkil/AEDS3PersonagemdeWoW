import struct
import os
from model.Conta import Conta
from controller.HashExtensivel import HashExtensivel

class ContaDAO:
    def __init__(self, arquivo="dados/contas.bin"):
        self.arquivo = arquivo
        self.header_fmt = "<i"
        self.header_size = struct.calcsize(self.header_fmt)
        self.reg_size = struct.calcsize(Conta.FORMATO)
        self.hash = HashExtensivel("dados/index_contas")
        
        if not os.path.exists(self.arquivo):
            os.makedirs(os.path.dirname(self.arquivo), exist_ok=True)
            with open(self.arquivo, "wb") as f:
                f.write(struct.pack(self.header_fmt, 0))
                
    def create(self, conta):
        with open(self.arquivo, "rb+") as f: 
            f.seek(0)
            ultimo_id = struct.unpack(self.header_fmt, f.read(self.header_size))[0]
            novo_id = ultimo_id + 1
            conta.id = novo_id
            
            f.seek(0, 2)
            pos = f.tell(0)
            f.write(conta.to_bytes())
            self.hash.insert(novo_id, pos)

            f.seek(0)
            f.write(struct.pack(self.header_fmt, novo_id))
            print(f"Conta do usuário {novo_id} criada com sucesso!")

    def read(self, id_alvo):
        posicao = self.hash.search(id_alvo)
        if posicao is not None:
            with open(self.arquivo, "rb") as f:
                f.seek(posicao)
                dados = f.read(self.reg_size)
                if not dados: return None
                
                conta = Conta.from_bytes(dados)
                # O Hash encontrou o registro, agora só conferimos a lápide
                if conta.lapide == b' ':
                    return conta
        return None

    def read_por_usuario(self, nome_usuario):
        with open(self.arquivo, "rb") as f:
            f.seek(self.header_size)
            while True:
                posicao_atual = f.tell()
                lapide = f.read(1)
                if not lapide: break
                
                dados = f.read(self.reg_size - 1)
                usuario_lido = struct.unpack("<20s", dados[4:24])[0]
                usuario_limpo = usuario_lido.decode('utf-8').strip('\x00')

                if usuario_limpo == nome_usuario and lapide == b' ':
                    f.seek(posicao_atual)
                    return Conta.from_bytes(f.read(self.reg_size))
        return None
    
    def update(self, id_alvo, conta_atualizada):
        pos = self.hash.search(id_alvo)
        if pos != None:
            with open(self.arquivo, "rb+") as f:
                posicao_atual = f.tell()
                lapide = f.read(1)
                if not lapide:
                    return False
                # Lemos o ID (4 bytes) para comparar
                id_lido = struct.unpack("<i", f.read(4))[0]   
                if id_lido == id_alvo and lapide == b' ':
                    f.seek(posicao_atual)
                    f.write(conta_atualizada.to_bytes())
                    return True
                # Pula o restante do registro
                f.seek(posicao_atual + self.reg_size)
        return False
    
    def delete(self, id_alvo):
        posicao = self.hash.search(id_alvo)
        if posicao is not None:
            with open(self.arquivo, "rb+") as f:
                f.seek(posicao) # Pula direto para o registro
                f.write(b'*')   # Marca a lápide na primeira posição do registro
                print(f"Conta ID {id_alvo} excluída com sucesso!")
                return True
        return False