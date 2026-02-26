import struct
import os

class GrupoTemp:
    FORMATO = "<1s i i i" 

    def __init__(self, id_grupo, id_conta, id_personagem, lapide=b' '):
        self.id_grupo = id_grupo
        self.id_conta = id_conta
        self.id_personagem = id_personagem
        self.lapide = lapide
    
    def to_bytes(self):
        return struct.pack(self.FORMATO, self.lapide, self.id_grupo, self.id_conta, self.id_personagem)
    
    @classmethod
    def from_bytes(cls, dados_binarios):
        lapide, id_g, id_c, id_p = struct.unpack(cls.FORMATO, dados_binarios)
        return cls(id_g, id_c, id_p, lapide)
    
class ArquivoGrupoTemp:
    def __init__(self, nome_arquivo="grupos_temp.bin"):
        self.nome_arquivo = nome_arquivo
        self.formato_header = "<i" 
        self.tamanho_header = struct.calcsize(self.formato_header)
        self.tamanho_registro = struct.calcsize(GrupoTemp.FORMATO)
        
        if not os.path.exists(self.nome_arquivo):
            with open(self.nome_arquivo, "wb") as f:
                f.write(struct.pack(self.formato_header, 0))

    def adicionarGrupo(self, id_grupo, id_conta, id_perso):
        with open(self.nome_arquivo, "rb+") as f:
            f.seek(self.tamanho_header)

            # Primeiro percorre o arquivo todo procurando duplicatas
            while True:
                lapide = f.read(1)
                if not lapide:
                    break # Chegou ao fim do arquivo sem achar erro, sai do loop
                
                dados = f.read(self.tamanho_registro - 1)
                id_g_lido, id_c_lido, id_p_lido = struct.unpack("<i i i", dados)

                if lapide == b' ' and id_c_lido == id_conta and id_grupo == id_g_lido:
                    print(f"\n[ERRO] A conta {id_conta} já possui um personagem (ID: {id_p_lido}) neste grupo!")
                    return False 

            f.seek(0, 2)
            novo_membro = GrupoTemp(id_grupo, id_conta, id_perso)
            f.write(novo_membro.to_bytes()) 
            print(f"\n[SUCESSO] Personagem {id_perso} adicionado ao Grupo {id_grupo}.")
            return True

    def remover_do_grupo_por_nome(self, id_grupo, nome_personagem, arquivo_personagem):
        id_p = arquivo_personagem.read_por_nome(nome_personagem)
        
        if id_p is None:
            print(f"Personagem '{nome_personagem}' não encontrado.")
            return False

        with open(self.nome_arquivo, "rb+") as f:
            f.seek(self.tamanho_header)
            while True:
                pos_lapide = f.tell()
                lapide = f.read(1)
                if not lapide: break
                
                dados = f.read(self.tamanho_registro - 1)
                id_g_lido, id_c_lido, id_p_lido = struct.unpack("<i i i", dados)

                if lapide == b' ' and id_g_lido == id_grupo and id_p_lido == id_p:
                    f.seek(pos_lapide)
                    f.write(b'*') # Exclusão Lógica
                    print(f"Personagem '{nome_personagem}' (ID: {id_p}) removido do grupo {id_grupo}.")
                    return True
        
        print(f"Personagem '{nome_personagem}' não está neste grupo.")
        return False