import os
import struct
from model.Personagem import Personagem
from model.ArvoreBPlus import ArvoreBPlus
from controller.HashExtensivel import HashExtensivel
from dao.BairroDAO import BairroDAO

class PersonagemDAO:
    def __init__(self, arquivo="dados/personagens.bin"):
        self.arquivo = arquivo
        self.header_fmt = "<i"
        self.header_size = struct.calcsize(self.header_fmt)
        # O novo tamanho do registro é 51 bytes (incluindo o ponteiro prox)
        self.reg_size = struct.calcsize(Personagem.FORMATO) 
        
        # 1. ÍNDICE PRIMÁRIO (Requisito b - PK)
        self.hash_id = HashExtensivel("dados/index_personagem_id")
        
        # 2. RELACIONAMENTO 1:N (Requisito b - Hash Extensível)
        # Mapeia ID_Conta -> Endereço do PRIMEIRO personagem dessa conta no .bin
        self.hash_relacao = HashExtensivel("dados/index_relacao_conta_perso")
        
        # 3. ÁRVORES B+ (Requisito d - Inserção e Busca)
        self.arvore_id = ArvoreBPlus("dados/index_perso_id", ordem=4)
        self.arvore_nivel = ArvoreBPlus("dados/index_perso_nivel", ordem=4)
        
        if not os.path.exists(self.arquivo):
            os.makedirs(os.path.dirname(self.arquivo), exist_ok=True)
            with open(self.arquivo, "wb") as f:
                f.write(struct.pack(self.header_fmt, 0))

    def create(self, personagem):
        """Cria o personagem e sincroniza todos os índices."""
        with open(self.arquivo, "rb+") as f:
            # Gerar novo ID
            f.seek(0)
            ultimo_id = struct.unpack(self.header_fmt, f.read(self.header_size))[0]
            novo_id = ultimo_id + 1
            personagem.id = novo_id
            
            # --- Lógica do Relacionamento 1:N (Lista Encadeada no Arquivo) ---
            # Busca se a conta já possui personagens no Hash de relação
            primeiro_da_conta = self.hash_relacao.search(personagem.id_conta)
            
            f.seek(0, 2)
            posicao_atual = f.tell()
            
            # O novo registro aponta para o antigo primeiro da lista (ou -1 se for o primeiro)
            personagem.prox = primeiro_da_conta if primeiro_da_conta is not None else -1
            
            # Grava o registro de 51 bytes
            f.write(personagem.to_bytes())

            # ATUALIZAÇÃO DOS ÍNDICES
            # Atualiza o índice primário por ID e os índices de busca por B+.
            self.hash_id.insert(novo_id, posicao_atual)
            try:
                self.arvore_id.inserir(novo_id, posicao_atual)      # B+ (ID)
                self.arvore_nivel.inserir(int(personagem.nivel), posicao_atual) # B+ (Nível)
            except Exception:
                pass
            
            # O Hash de relação agora aponta para este novo registro (topo da lista)
            self.hash_relacao.insert(personagem.id_conta, posicao_atual)

            # Atualiza o cabeçalho do arquivo .bin
            f.seek(0)
            f.write(struct.pack(self.header_fmt, novo_id))

        funcao_str = personagem.funcao.decode('utf-8').strip('\x00')
        print(f"Personagem {novo_id} ({funcao_str}) criado com sucesso!")

    def read(self, id_alvo):
        """Busca direta (O(1)) utilizando Hash Extensível.
        Se o índice estiver inconsistente, faz fallback para varredura completa do arquivo."""
        pos = self.hash_id.search(id_alvo)
        if pos is not None:
            with open(self.arquivo, "rb") as f:
                f.seek(pos)
                dados = f.read(self.reg_size)
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
        """Busca utilizando o índice de Árvore B+ (Requisito d)."""
        pos = self.arvore_id.buscar(id_alvo)
        if pos is not None:
            with open(self.arquivo, "rb") as f:
                f.seek(pos)
                p = Personagem.from_bytes(f.read(self.reg_size))
                if p.lapide == b' ':
                    return p
        return None

    def listar_por_conta(self, id_conta_alvo):
        """Lista personagens da conta usando o Hash de Relacionamento (1:N)."""
        # Pega o endereço do primeiro personagem da conta no Hash
        pos = self.hash_relacao.search(id_conta_alvo)
        
        if pos is None or pos == -1:
            return False

        with open(self.arquivo, "rb") as f:
            # Navega pela lista encadeada através dos ponteiros 'prox' salvos no .bin
            while pos != -1:
                f.seek(pos)
                dados = f.read(self.reg_size)
                if not dados: break
                
                p = Personagem.from_bytes(dados)
                if p.lapide == b' ':
                    n_limpo = p.nome.decode('utf-8').strip('\x00')
                    f_limpa = p.funcao.decode('utf-8').strip('\x00')
                    print(f"{p.id:<5} | {n_limpo:<20} | {p.nivel:<10.2f} | {f_limpa:<10}")
                
                # Move para o próximo registro da mesma conta
                pos = p.prox
        return True

    def buscar_por_nivel(self, nivel):
        """Busca por nível utilizando a Árvore B+."""
        pos = self.arvore_nivel.buscar(int(nivel))
        if pos is not None:
            with open(self.arquivo, "rb") as f:
                f.seek(pos)
                p = Personagem.from_bytes(f.read(self.reg_size))
                if p.lapide == b' ':
                    return [p]
        return []

    def update(self, id_alvo, novo_nome, novo_nivel, id_conta, nova_funcao):
        """Atualização indexada."""
        pos = self.hash_id.search(id_alvo)
        if pos is not None:
            with open(self.arquivo, "rb+") as f:
                f.seek(pos)
                # Lê o registro antigo para preservar o ponteiro da lista encadeada (prox)
                p_antigo = Personagem.from_bytes(f.read(self.reg_size))
                
                f.seek(pos)
                p_novo = Personagem(id_alvo, novo_nome, novo_nivel, id_conta, nova_funcao)
                p_novo.prox = p_antigo.prox # Mantém a integridade da lista 1:N
                f.write(p_novo.to_bytes())
                return True
        return False

    def delete(self, id_alvo):
        """Exclusão lógica indexada."""
        pos = self.hash_id.search(id_alvo)
        if pos is not None:
            with open(self.arquivo, "rb+") as f:
                f.seek(pos)
                f.write(b'*') # Marca lápide
            
            # Remove do hash para não deixar índice poluído
            self.hash_id.remover(id_alvo)
            # Cascade: remove relações N:N onde esse personagem aparece
            try:
                BairroDAO().remover_relacoes_por_personagem(id_alvo)
            except Exception:
                pass

            return True
        return False