import struct
import os

class Conta:
    # Adicionado o prefixo '<' para garantir tamanho fixo padrão (65 bytes)
    # 1s (1) + i (4) + 20s (20) + 30s (30) + 10s (10) = 65 bytes
    FORMATO = "<1s i 20s 30s 10s" 

    def __init__(self, id, usuario, email, data, lapide=b' '):
        self.id = id
        if isinstance(usuario, str):
            usuario = usuario.encode('utf-8')
        if isinstance(email, str):
            email = email.encode('utf-8')
        if isinstance(data, str):
            data = data.encode('utf-8')
            
        self.usuario = usuario[:20]
        self.email = email[:30]
        self.data = data[:10]
        self.lapide = lapide

    def to_bytes(self):      
        usuario_f = self.usuario.ljust(20, b'\x00')
        email_f = self.email.ljust(30, b'\x00')
        data_f = self.data.ljust(10, b'\x00')
        return struct.pack(self.FORMATO, self.lapide, self.id, usuario_f, email_f, data_f)
    
    @classmethod 
    def from_bytes(cls, dados_binarios):
        # Usando o prefixo '<' no unpack também
        lapide, id, usuario, email, data = struct.unpack(cls.FORMATO, dados_binarios)
        return cls(
            id, 
            usuario.decode('utf-8').strip('\x00'), 
            email.decode('utf-8').strip('\x00'), 
            data.decode('utf-8').strip('\x00'), 
            lapide
        )

class ArquivoConta:
    def __init__(self, nome_arquivo="contas.bin"):
        self.nome_arquivo = nome_arquivo
        self.formato_header = "<i" # Padronizado com <
        self.tamanho_header = struct.calcsize(self.formato_header)
        self.tamanho_registro = struct.calcsize(Conta.FORMATO)
        
        if not os.path.exists(self.nome_arquivo):
            with open(self.nome_arquivo, "wb") as f:
                f.write(struct.pack(self.formato_header, 0))
    
    def create(self, conta):
        with open(self.nome_arquivo, "rb+") as f:
            f.seek(0)
            ultimo_id = struct.unpack(self.formato_header, f.read(self.tamanho_header))[0]
            novo_id = ultimo_id + 1
            conta.id = novo_id
            
            f.seek(0, 2)
            f.write(conta.to_bytes())

            f.seek(0)
            f.write(struct.pack(self.formato_header, novo_id))
            print(f"Conta do usuário {novo_id} criada com sucesso!")

    def read(self, id_alvo):
        with open(self.nome_arquivo, "rb") as f:
            f.seek(self.tamanho_header)
            while True:
                posicao_atual = f.tell()
                lapide = f.read(1)
                if not lapide: break
                
                dados = f.read(self.tamanho_registro - 1)
                # IMPORTANTE: Adicionado '<' no unpack do ID para bater com a gravação
                id_lido = struct.unpack("<i", dados[:4])[0]

                if id_lido == id_alvo and lapide == b' ':
                    f.seek(posicao_atual)
                    return Conta.from_bytes(f.read(self.tamanho_registro))
        return None

    def read_por_usuario(self, nome_usuario):
        with open(self.nome_arquivo, "rb") as f:
            f.seek(self.tamanho_header)
            while True:
                posicao_atual = f.tell()
                lapide = f.read(1)
                if not lapide: break
                
                dados = f.read(self.tamanho_registro - 1)
                # Desempacota o usuário (está após o ID de 4 bytes)
                usuario_lido = struct.unpack("<20s", dados[4:24])[0]
                usuario_limpo = usuario_lido.decode('utf-8').strip('\x00')

                if usuario_limpo == nome_usuario and lapide == b' ':
                    f.seek(posicao_atual)
                    return Conta.from_bytes(f.read(self.tamanho_registro))
        return None

    def update(self, id_alvo, novo_usuario, novo_email, nova_data):
        with open(self.nome_arquivo, "rb+") as f:
            f.seek(self.tamanho_header)
            while True:
                posicao_atual = f.tell()
                lapide = f.read(1)
                if not lapide: break

                dados = f.read(self.tamanho_registro - 1)
                id_lido = struct.unpack("<i", dados[:4])[0]

                if id_lido == id_alvo and lapide == b' ':
                    f.seek(posicao_atual)
                    conta_up = Conta(id_alvo, novo_usuario, novo_email, nova_data)
                    f.write(conta_up.to_bytes())
                    print(f"Conta {id_alvo} atualizada!")
                    return True
        return False

    def delete(self, id_alvo):
        with open(self.nome_arquivo, "rb+") as f:
            f.seek(self.tamanho_header)
            while True:
                pos_lapide = f.tell()
                lapide = f.read(1)
                if not lapide: break
                
                dados = f.read(self.tamanho_registro - 1)
                id_lido = struct.unpack("<i", dados[:4])[0]

                if lapide == b' ' and id_lido == id_alvo:
                    f.seek(pos_lapide)
                    f.write(b'*')
                    return True
        return False