import struct
import os
from model.Conta import Conta

class ContaDAO:
    def __init__(self, arquivo="dados/contas.bin"):
        self.arquivo = arquivo
        self.header_fmt = "<i"
        self.header_size = struct.calcsize(self.header_fmt)
        self.reg_size = struct.calcsize(Conta.FORMATO)
        
        if not os.path.exists(self.arquivo):
            os.makedirs(os.path.dirname(self.arquivo), exist_ok=True)
            with open(self.arquivo, "wb") as f:
                f.write(struct.pack(self.header_fmt, 0))
                
    def create(self, conta):
        with open(self.arquivo, "rb+") as f: # Corrigido: self.arquivo
            f.seek(0)
            ultimo_id = struct.unpack(self.header_fmt, f.read(self.header_size))[0]
            novo_id = ultimo_id + 1
            conta.id = novo_id
            
            f.seek(0, 2)
            f.write(conta.to_bytes())

            f.seek(0)
            f.write(struct.pack(self.header_fmt, novo_id))
            print(f"Conta do usuário {novo_id} criada com sucesso!")

    def read(self, id_alvo):
        with open(self.arquivo, "rb") as f:
            f.seek(self.header_size)
            while True:
                posicao_atual = f.tell()
                lapide = f.read(1)
                if not lapide: break
                
                dados = f.read(self.reg_size - 1)
                id_lido = struct.unpack("<i", dados[:4])[0]

                if id_lido == id_alvo and lapide == b' ':
                    f.seek(posicao_atual)
                    return Conta.from_bytes(f.read(self.reg_size))
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