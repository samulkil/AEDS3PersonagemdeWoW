import struct
import os

class Intermediaria:
    # O prefixo '<' garante que o tamanho seja exatamente 9 bytes
    FORMATO = "<1s i i" 

    def __init__(self, id_personagem, id_bairro, lapide=b' '):
        self.id_personagem = id_personagem
        self.id_bairro = id_bairro
        self.lapide = lapide

    def to_bytes(self):
        return struct.pack(self.FORMATO, self.lapide, self.id_personagem, self.id_bairro)
    
    @classmethod
    def from_bytes(cls, dados_binarios):
        # Uso do prefixo '<' para desempacotar com precisão
        lapide, id_p, id_b = struct.unpack(cls.FORMATO, dados_binarios)
        return cls(id_p, id_b, lapide)

class ArquivoIntermediaria:
    def __init__(self, nome_arquivo="personagem_bairro.bin"):
        self.nome_arquivo = nome_arquivo
        self.tamanho_header = 4 
        self.tamanho_registro = struct.calcsize(Intermediaria.FORMATO)
        
        if not os.path.exists(self.nome_arquivo):
            with open(self.nome_arquivo, "wb") as f:
                # Cabeçalho padronizado também
                f.write(struct.pack("<i", 0))
    
    def vincular(self, id_personagem, id_bairro):
        with open(self.nome_arquivo, "rb+") as f:
            f.seek(0, 2)
            novo_vinculo = Intermediaria(id_personagem, id_bairro)
            f.write(novo_vinculo.to_bytes())
            print(f"Vínculo criado: Personagem {id_personagem} -> Bairro {id_bairro}")

    def listar_bairros_do_personagem(self, id_p_alvo):
        bairros = []
        with open(self.nome_arquivo, "rb") as f:
            f.seek(self.tamanho_header)
            while True:
                lapide = f.read(1)
                if not lapide: break
                
                dados = f.read(self.tamanho_registro - 1)
                # IMPORTANTE: Usar o '<' no unpack aqui também
                id_p, id_b = struct.unpack("<i i", dados)

                if lapide == b' ' and id_p == id_p_alvo:
                    bairros.append(id_b)
        return bairros

    def desvincular(self, id_p, id_b):
        with open(self.nome_arquivo, "rb+") as f:
            f.seek(self.tamanho_header)
            while True:
                posicao_da_lapide = f.tell()
                lapide = f.read(1)
                if not lapide: break
                
                dados = f.read(self.tamanho_registro - 1)
                id_p_lido, id_b_lido = struct.unpack("<i i", dados)

                if lapide == b' ' and id_p_lido == id_p and id_b_lido == id_b:
                    f.seek(posicao_da_lapide)
                    f.write(b'*')
                    print("Vínculo removido com sucesso.")
                    return True
        return False