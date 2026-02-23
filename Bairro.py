import struct
import os

class Bairro:
    # Formato: 1s (Lápide), i (ID), 30s (Nome do Bairro)
    FORMATO = "1s i 30s" 

    def __init__(self, id, nome, lapide=b' '):
        self.id = id
        # Garante que o nome tenha no máximo 30 bytes
        if isinstance(nome, str):
            nome = nome.encode('utf-8')
        self.nome = nome[:30]
        self.lapide = lapide

    def to_bytes(self):      
        nome_f = self.nome.ljust(30, b'\x00')
        return struct.pack(self.FORMATO, self.lapide, self.id, nome_f)
    
    @classmethod 
    def from_bytes(cls, dados_binarios):
        lapide, id, nome = struct.unpack(cls.FORMATO, dados_binarios)
        return cls(id, nome.decode('utf-8').strip('\x00'), lapide)

class ArquivoBairro:
    def __init__(self, nome_arquivo="bairros.bin"):
        self.nome_arquivo = nome_arquivo
        self.formato_header = "i" 
        self.tamanho_header = struct.calcsize(self.formato_header)
        self.tamanho_registro = struct.calcsize(Bairro.FORMATO)
        
        if not os.path.exists(self.nome_arquivo):
            with open(self.nome_arquivo, "wb") as f:
                f.write(struct.pack(self.formato_header, 0))
    
    def update(self, id_alvo, novo_nome):
        """Atualiza o nome de um bairro existente (Fase 1)"""
        with open(self.nome_arquivo, "rb+") as f:
            f.seek(self.tamanho_header) # Pula os 4 bytes do ID de controle
            
            while True:
                posicao_atual = f.tell() # Guarda onde o registro começa
                lapide = f.read(1)
                
                if not lapide:
                    print("Bairro não encontrado.")
                    break

                # Lê o restante do registro (ID + Nome)
                dados_restantes = f.read(self.tamanho_registro - 1)
                id_lido = struct.unpack("i", dados_restantes[:4])[0]

                # Se o ID bater e não estiver excluído logicamente
                if id_lido == id_alvo and lapide == b' ':
                    f.seek(posicao_atual) # Volta para o início do registro
                    
                    # Cria um novo objeto com o nome atualizado
                    novo_bairro = Bairro(id_alvo, novo_nome)
                    
                    # Sobrescreve os bytes no arquivo
                    f.write(novo_bairro.to_bytes())
                    print(f"Bairro {id_alvo} atualizado com sucesso!")
                    return True
        return False
    
    def create(self, bairro):
        with open(self.nome_arquivo, "rb+") as f:
            f.seek(0)
            ultimo_id = struct.unpack(self.formato_header, f.read(self.tamanho_header))[0]
            novo_id = ultimo_id + 1
            bairro.id = novo_id
            
            f.seek(0, 2)
            f.write(bairro.to_bytes())

            f.seek(0)
            f.write(struct.pack(self.formato_header, novo_id))
            print(f"Bairro {novo_id} cadastrado!")

    def read(self, id_alvo):
        with open(self.nome_arquivo, "rb") as f:
            f.seek(self.tamanho_header)
            while True:
                posicao_atual = f.tell()
                lapide = f.read(1)
                if not lapide: break
                
                dados = f.read(self.tamanho_registro - 1)
                id_lido = struct.unpack("i", dados[:4])[0]

                if id_lido == id_alvo and lapide == b' ':
                    f.seek(posicao_atual)
                    return Bairro.from_bytes(f.read(self.tamanho_registro))
        return None

    def delete(self, id_alvo):
        with open(self.nome_arquivo, "rb+") as f:
            f.seek(self.tamanho_header)
            while True:
                pos_lapide = f.tell()
                lapide = f.read(1)
                if not lapide: break
                
                dados = f.read(self.tamanho_registro - 1)
                id_lido = struct.unpack("i", dados[:4])[0]

                if lapide == b' ' and id_lido == id_alvo:
                    f.seek(pos_lapide)
                    f.write(b'*')
                    return True
        return False