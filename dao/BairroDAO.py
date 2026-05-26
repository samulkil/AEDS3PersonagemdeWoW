import os
import struct
from model.Bairro import Bairro
from model.BairroPersonagem import BairroPersonagem
from model.ArvoreBPlus import ArvoreBPlus
from controller.HashExtensivel import HashExtensivel

class BairroDAO:
    def __init__(self, arquivo="dados/bairros.bin", arquivo_relacao="dados/bairro_personagem.bin"):
        self.arquivo = arquivo
        self.arquivo_relacao = arquivo_relacao
        self.header_fmt = "<i"
        self.header_size = struct.calcsize(self.header_fmt)
        self.reg_size = struct.calcsize(Bairro.FORMATO)
        self.reg_relacao_size = struct.calcsize(BairroPersonagem.FORMATO)
        
        self.arvore_id = ArvoreBPlus("dados/index_bairro_id", ordem=4)
        
        self.arvore_dono = ArvoreBPlus("dados/index_bairro_dono", ordem=4)
        
        self.hash_relacao = HashExtensivel("dados/index_bairro_personagem")
        
        if not os.path.exists(self.arquivo):
            os.makedirs(os.path.dirname(self.arquivo), exist_ok=True)
            with open(self.arquivo, "wb") as f:
                f.write(struct.pack(self.header_fmt, 0))
        
        if not os.path.exists(self.arquivo_relacao):
            os.makedirs(os.path.dirname(self.arquivo_relacao), exist_ok=True)
            with open(self.arquivo_relacao, "wb") as f:
                f.write(b"")

    def create(self, bairro):
        """Cria um novo bairro e indexa nas Ãrvores B+."""
        with open(self.arquivo, "rb+") as f:
            f.seek(0)
            ultimo_id = struct.unpack(self.header_fmt, f.read(self.header_size))[0]
            novo_id = ultimo_id + 1
            bairro.id = novo_id
            
            f.seek(0, 2)
            posicao_atual = f.tell()
            
            f.write(bairro.to_bytes())
            
            try:
                self.arvore_id.inserir(novo_id, posicao_atual)
            except Exception:
                pass
            
            try:
                self.arvore_dono.inserir(bairro.id_dono, posicao_atual)
            except Exception:
                pass
            
            f.seek(0)
            f.write(struct.pack(self.header_fmt, novo_id))
        
        nome_bairro = bairro.nome.decode('utf-8').strip('\x00')
        print(f"Bairro {novo_id} ({nome_bairro}) criado com sucesso! Dono: {bairro.id_dono}")
        return novo_id

    def read(self, id_alvo):
        """Busca um bairro pelo ID usando Ãrvore B+."""
        pos = self.arvore_id.buscar(id_alvo)
        if pos is not None:
            with open(self.arquivo, "rb") as f:
                f.seek(pos)
                dados = f.read(self.reg_size)
                if len(dados) == self.reg_size:
                    b = Bairro.from_bytes(dados)
                    if b.lapide == b' ':
                        return b

        with open(self.arquivo, "rb") as f:
            f.seek(self.header_size)
            while True:
                dados = f.read(self.reg_size)
                if len(dados) != self.reg_size:
                    break
                b = Bairro.from_bytes(dados)
                if b.id == id_alvo and b.lapide == b' ':
                    return b
        return None

    def listar_todos(self):
        """Lista todos os bairros."""
        with open(self.arquivo, "rb") as f:
            f.seek(self.header_size)
            while True:
                dados = f.read(self.reg_size)
                if len(dados) != self.reg_size:
                    break
                b = Bairro.from_bytes(dados)
                if b.lapide == b' ':
                    nome_limpo = b.nome.decode('utf-8').strip('\x00')
                    print(f"{b.id:<5} | {nome_limpo:<30} | Dono: {b.id_dono}")

    def listar_todos_objetos(self):
        """Retorna todos os bairros ativos como objetos."""
        bairros = []
        with open(self.arquivo, "rb") as f:
            f.seek(self.header_size)
            while True:
                dados = f.read(self.reg_size)
                if len(dados) != self.reg_size:
                    break
                b = Bairro.from_bytes(dados)
                if b.lapide == b' ':
                    bairros.append(b)
        return bairros

    def buscar_por_dono(self, id_dono):
        """Busca bairros pelo ID do dono usando Ãrvore B+."""
        posicoes = self.arvore_dono.buscar_todos(id_dono)
        bairros = []
        
        for pos in posicoes:
            with open(self.arquivo, "rb") as f:
                f.seek(pos)
                dados = f.read(self.reg_size)
                if len(dados) == self.reg_size:
                    b = Bairro.from_bytes(dados)
                    if b.lapide == b' ' and b.id_dono == id_dono:
                        bairros.append(b)
        
        return bairros

    def update(self, id_alvo, novo_nome, novo_id_dono):
        """Atualiza um bairro."""
        pos = self.hash_id.search(id_alvo)
        if pos is not None:
            with open(self.arquivo, "rb+") as f:
                f.seek(pos)
                _b_antigo = Bairro.from_bytes(f.read(self.reg_size))
                
                f.seek(pos)
                b_novo = Bairro(id_alvo, novo_nome, novo_id_dono)
                f.write(b_novo.to_bytes())
                return True
        return False

    def delete(self, id_alvo):
        """ExclusÃ£o lÃ³gica de um bairro."""
        pos = self.arvore_id.buscar(id_alvo)
        if pos is not None:
            with open(self.arquivo, "rb+") as f:
                f.seek(pos)
                f.write(b'*')
            try:
                self.remover_todas_relacoes_do_bairro(id_alvo)
            except Exception:
                pass

            return True
        return False

    def adicionar_personagem(self, id_bairro, id_personagem):
        """Adiciona um personagem ao bairro (relacionamento N:N)."""
        if self._relacao_existe(id_bairro, id_personagem):
            print("[Erro] Este personagem jÃ¡ estÃ¡ neste bairro!")
            return False

        with open(self.arquivo_relacao, "rb+") as f:
            primeiro = self.hash_relacao.search(id_bairro)
            
            f.seek(0, 2)
            posicao_atual = f.tell()
            
            relacao = BairroPersonagem(id_bairro, id_personagem)
            relacao.prox = primeiro if primeiro is not None else -1
            
            f.write(relacao.to_bytes())
            
            try:
                self.hash_relacao.insert(id_bairro, posicao_atual)
            except Exception:
                pass
        
        print(f"Personagem {id_personagem} adicionado ao Bairro {id_bairro}!")
        return True

    def remover_personagem(self, id_bairro, id_personagem):
        """Remove um personagem do bairro."""
        pos = self.hash_relacao.search(id_bairro)
        
        if pos is None:
            print("[Erro] Bairro nÃ£o possui personagens!")
            return False

        removido = False
        primeira_pos = None

        with open(self.arquivo_relacao, "rb+") as f:
            pos_temp = pos
            while pos_temp != -1:
                f.seek(pos_temp)
                dados = f.read(self.reg_relacao_size)
                if len(dados) != self.reg_relacao_size:
                    break
                
                relacao = BairroPersonagem.from_bytes(dados)
                
                if relacao.id_bairro == id_bairro and relacao.id_personagem == id_personagem and relacao.lapide == b' ':
                    f.seek(pos_temp)
                    f.write(b'*')
                    removido = True
                else:
                    if relacao.lapide == b' ' and (primeira_pos is None or relacao.id_bairro == id_bairro):
                        primeira_pos = pos_temp
                
                pos_temp = relacao.prox
        
        if removido:
            print(f"Personagem {id_personagem} removido do Bairro {id_bairro}!")
            return True
        else:
            print("[Erro] Personagem nÃ£o encontrado neste bairro!")
            return False

    def listar_personagens_do_bairro(self, id_bairro):
        """Lista todos os personagens de um bairro."""
        pos = self.hash_relacao.search(id_bairro)
        
        if pos is None:
            print("[Aviso] Este bairro nÃ£o possui personagens.")
            return False

        encontrou = False
        with open(self.arquivo_relacao, "rb") as f:
            while pos != -1:
                f.seek(pos)
                dados = f.read(self.reg_relacao_size)
                if not dados:
                    break
                
                relacao = BairroPersonagem.from_bytes(dados)
                
                if relacao.id_bairro == id_bairro and relacao.lapide == b' ':
                    print(f"  - Personagem ID: {relacao.id_personagem}")
                    encontrou = True
                
                pos = relacao.prox
        
        return encontrou

    def _reconstruir_encadeamento_bairro(self, id_bairro):
        """ReconstrÃ³i o ponteiro inicial do hash_relacao para um bairro.
        Encontra o primeiro relacionamento ativo (se houver) e atualiza o hash;
        caso contrÃ¡rio remove a chave do hash.
        """
        primeiro = None
        if not os.path.exists(self.arquivo_relacao):
            try:
                self.hash_relacao.remover(id_bairro)
            except Exception:
                pass
            return

        with open(self.arquivo_relacao, "rb") as f:
            pos = 0
            while True:
                dados = f.read(self.reg_relacao_size)
                if len(dados) != self.reg_relacao_size:
                    break
                rel = BairroPersonagem.from_bytes(dados)
                if rel.id_bairro == id_bairro and rel.lapide == b' ':
                    primeiro = pos
                    break
                pos += self.reg_relacao_size

        try:
            if primeiro is None:
                self.hash_relacao.remover(id_bairro)
            else:
                self.hash_relacao.insert(id_bairro, primeiro)
        except Exception:
            pass

    def remover_relacoes_por_personagem(self, id_personagem):
        """Marca como excluÃ­dos todos os relacionamentos onde aparece o personagem.
        Depois reconstrÃ³i os ponteiros iniciais dos bairros afetados.
        """
        if not os.path.exists(self.arquivo_relacao):
            return False

        afetados = set()
        with open(self.arquivo_relacao, "rb+") as f:
            pos = 0
            while True:
                dados = f.read(self.reg_relacao_size)
                if len(dados) != self.reg_relacao_size:
                    break
                rel = BairroPersonagem.from_bytes(dados)
                if rel.id_personagem == id_personagem and rel.lapide == b' ':
                    f.seek(pos)
                    f.write(b'*')
                    afetados.add(rel.id_bairro)
                pos += self.reg_relacao_size

        for b in afetados:
            self._reconstruir_encadeamento_bairro(b)

        return True

    def remover_todas_relacoes_do_bairro(self, id_bairro):
        """Marca como excluÃ­dos todos os relacionamentos de um bairro e remove a chave do hash."""
        if not os.path.exists(self.arquivo_relacao):
            try:
                self.hash_relacao.remover(id_bairro)
            except Exception:
                pass
            return False

        removido = False
        with open(self.arquivo_relacao, "rb+") as f:
            pos = 0
            while True:
                dados = f.read(self.reg_relacao_size)
                if len(dados) != self.reg_relacao_size:
                    break
                rel = BairroPersonagem.from_bytes(dados)
                if rel.id_bairro == id_bairro and rel.lapide == b' ':
                    f.seek(pos)
                    f.write(b'*')
                    removido = True
                pos += self.reg_relacao_size

        try:
            self.hash_relacao.remover(id_bairro)
        except Exception:
            pass

        return removido

    def _relacao_existe(self, id_bairro, id_personagem):
        """Verifica se uma relaÃ§Ã£o jÃ¡ existe."""
        pos = self.hash_relacao.search(id_bairro)
        
        if pos is None:
            return False

        with open(self.arquivo_relacao, "rb") as f:
            while pos != -1:
                f.seek(pos)
                dados = f.read(self.reg_relacao_size)
                if not dados:
                    break
                
                relacao = BairroPersonagem.from_bytes(dados)
                
                if (relacao.id_bairro == id_bairro and 
                    relacao.id_personagem == id_personagem and 
                    relacao.lapide == b' '):
                    return True
                
                pos = relacao.prox
        
        return False

    def listar_todos_ordenado_por_id(self):
        """Lista todos os bairros ORDENADOS por ID usando Ãrvore B+ (sem ordenaÃ§Ã£o em memÃ³ria).
        
        Percorre a estrutura de folhas encadeadas da Ãrvore B+ para garantir ordem.
        Isso demonstra a aplicaÃ§Ã£o prÃ¡tica de B+ tree para recuperaÃ§Ã£o de dados em ordem.
        
        Returns:
            list: Lista de objetos Bairro ordenados por ID
        """
        bairros = []
        
        try:
            raiz_offset = self.arvore_id._ler_raiz()
            if raiz_offset == -1:
                return bairros
            
            no = self.arvore_id._ler_no(raiz_offset)
            
            while not no.eh_folha:
                if no.ponteiros and no.ponteiros[0] not in (None, -1, 0):
                    no = self.arvore_id._ler_no(no.ponteiros[0])
                else:
                    return bairros
            
            while no is not None:
                for i, id_bairro in enumerate(no.chaves):
                    pos = no.ponteiros[i]
                    
                    with open(self.arquivo, "rb") as f:
                        f.seek(pos)
                        dados = f.read(self.reg_size)
                        if len(dados) == self.reg_size:
                            b = Bairro.from_bytes(dados)
                            if b.lapide == b' ':
                                bairros.append(b)
                
                if no.proximo == -1 or no.proximo is None:
                    break
                
                no = self.arvore_id._ler_no(no.proximo)
        
        except Exception as e:
            print(f"[Erro] Ao listar ordenado: {e}")
            return bairros
        
        return bairros
