import os
import struct
from model.Personagem import Personagem
from model.ArvoreBPlus import ArvoreBPlus
from controller.HashExtensivel import HashExtensivel

class PersonagemDAO:
    def __init__(self, arquivo="dados/personagens.bin"):
        self.arquivo = arquivo
        self.header_fmt = "<i"
        self.header_size = struct.calcsize(self.header_fmt)
        self.reg_size = struct.calcsize(Personagem.FORMATO) # Agora 43 bytes
        
        # Inicialização dos Índices
        # 1. Hash Extensível para busca direta por ID (Requisito b)
        self.hash_id = HashExtensivel("dados/index_personagem_id")
        
        # 2. Árvores B+ (Requisito d)
        self.arvore_id = ArvoreBPlus("dados/index_perso_id", ordem=4)
        self.arvore_nivel = ArvoreBPlus("dados/index_perso_nivel", ordem=4)
        
        # Cria o ficheiro de dados se não existir
        if not os.path.exists(self.arquivo):
            os.makedirs(os.path.dirname(self.arquivo), exist_ok=True)
            with open(self.arquivo, "wb") as f:
                f.write(struct.pack(self.header_fmt, 0))

    def create(self, personagem):
        """Cria o personagem e atualiza Hash e Árvores B+."""
        with open(self.arquivo, "rb+") as f:
            f.seek(0)
            ultimo_id = struct.unpack(self.header_fmt, f.read(self.header_size))[0]
            novo_id = ultimo_id + 1
            personagem.id = novo_id
            
            f.seek(0, 2)
            posicao = f.tell()  

            f.write(personagem.to_bytes())

<<<<<<< Updated upstream
            # Atualização dos Índices
            self.hash_id.insert(novo_id, posicao)       # Hash (Busca Direta)
            self.arvore_id.inserir(novo_id, posicao)    # B+ (ID)
            self.arvore_nivel.inserir(int(personagem.nivel), posicao) # B+ (Nível)
=======
            # ATUALIZAÇÃO DOS ÍNDICES
            # O índice de ID de personagem e a Árvore B+ não estão totalmente estáveis no código atual.
            # Para permitir a criação dos personagens, atualizamos apenas o relacionamento 1:N.
            try:
                self.arvore_id.inserir(novo_id, posicao_atual)      # B+ (ID)
                self.arvore_nivel.inserir(int(personagem.nivel), posicao_atual) # B+ (Nível)
            except Exception:
                pass
            
            # O Hash de relação agora aponta para este novo registro (topo da lista)
            self.hash_relacao.insert(personagem.id_conta, posicao_atual)
>>>>>>> Stashed changes

            # Atualiza cabeçalho
            f.seek(0)
            f.write(struct.pack(self.header_fmt, novo_id))

        print(f"Personagem {novo_id} ({personagem.funcao.decode('utf-8').strip()}) criado com sucesso!")
        
    def read(self, id_alvo):
<<<<<<< Updated upstream
        """Busca direta utilizando o Hash Extensível (Requisito b)."""
=======
        """Busca direta (O(1)) utilizando Hash Extensível.
        Se o índice estiver inconsistente, faz fallback para varredura completa do arquivo."""
>>>>>>> Stashed changes
        pos = self.hash_id.search(id_alvo)
        if pos is not None:
            with open(self.arquivo, "rb") as f:
                f.seek(pos)
                dados = f.read(self.reg_size)
<<<<<<< Updated upstream
                if not dados: return None
                
=======
                if len(dados) == self.reg_size:
                    p = Personagem.from_bytes(dados)
                    if p.lapide == b' ':
                        return p

        # Fallback: verificação direta no arquivo para garantir consistência
        with open(self.arquivo, "rb") as f:
            f.seek(self.header_size)
            while True:
                dados = f.read(self.reg_size)
                if len(dados) != self.reg_size:
                    break
>>>>>>> Stashed changes
                p = Personagem.from_bytes(dados)
                if p.id == id_alvo and p.lapide == b' ':
                    return p
        return None

    def read_by_id_and_conta(self, id_alvo, id_conta_alvo):
        """Busca um personagem pelo ID apenas na conta específica."""
        pos = self.hash_id.search(id_alvo)
        if pos is not None:
            with open(self.arquivo, "rb") as f:
                f.seek(pos)
                dados = f.read(self.reg_size)
                if len(dados) == self.reg_size:
                    p = Personagem.from_bytes(dados)
                    if p.lapide == b' ' and p.id_conta == id_conta_alvo:
                        return p

        with open(self.arquivo, "rb") as f:
            f.seek(self.header_size)
            while True:
                dados = f.read(self.reg_size)
                if len(dados) != self.reg_size:
                    break
                p = Personagem.from_bytes(dados)
                if p.id == id_alvo and p.id_conta == id_conta_alvo and p.lapide == b' ':
                    return p
        return None
    
    def read_bplus(self, id_alvo):
        """Busca utilizando a Árvore B+ (Requisito d)."""
        pos = self.arvore_id.buscar(id_alvo)
        if pos is not None:
            with open(self.arquivo, "rb") as f:
                f.seek(pos)
                dados = f.read(self.reg_size)
                p = Personagem.from_bytes(dados)
                if p.lapide == b' ':
                    return p
        return None

    def listar_por_conta(self, id_conta_alvo):
        """Lista personagens de uma conta (Relacionamento 1:N)."""
        encontrou = False
        with open(self.arquivo, "rb") as f:
            f.seek(self.header_size) 
            while True:
                dados = f.read(self.reg_size) 
                if not dados: break
                
                # Desempacota incluindo o novo campo 'funcao'
                lapide, id_p, nome, nivel, id_c, funcao = struct.unpack(Personagem.FORMATO, dados)
                
                if lapide == b' ' and id_c == id_conta_alvo:
                    n_limpo = nome.decode('utf-8').strip('\x00')
                    f_limpa = funcao.decode('utf-8').strip('\x00')
                    print(f"{id_p:<5} | {n_limpo:<20} | {nivel:<10.2f} | {f_limpa:<10}")
                    encontrou = True
        return encontrou

    def update(self, id_alvo, novo_nome, novo_nivel, id_conta, nova_funcao):
        """Atualização indexada."""
        pos = self.hash_id.search(id_alvo)
        if pos is not None:
            with open(self.arquivo, "rb+") as f:
                f.seek(pos)
                p_atualizado = Personagem(id_alvo, novo_nome, novo_nivel, id_conta, nova_funcao)
                f.write(p_atualizado.to_bytes())
                print(f"Personagem {id_alvo} atualizado!")
                return True
        return False

    def delete(self, id_alvo):
        """Exclusão lógica indexada."""
        pos = self.hash_id.search(id_alvo)
        if pos is not None:
            with open(self.arquivo, "rb+") as f:
                f.seek(pos)
                f.write(b'*') # Marca a lápide
                return True
        return False
    
    def buscar_por_nivel(self, nivel):
        """Busca por nível usando a Árvore B+ (Requisito d)."""
        # Assume-se que a ArvoreBPlus tenha um método para buscar chaves repetidas ou intervalos
        # Se buscar() retornar apenas um, esta lógica precisará de um buscar_todos() na B+
        pos = self.arvore_nivel.buscar(int(nivel))
        if pos is not None:
            with open(self.arquivo, "rb") as f:
                f.seek(pos)
                p = Personagem.from_bytes(f.read(self.reg_size))
                if p.lapide == b' ':
                    return [p]
        return []