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
        self.reg_size = struct.calcsize(Personagem.FORMATO)
        self.hash_id = HashExtensivel("dados/index_personagem_id")
        self.hash_relacao = HashExtensivel("dados/index_relacao_conta_perso")
        self.arvore_id = ArvoreBPlus("dados/index_perso_id", ordem=4)
        self.arvore_nivel = ArvoreBPlus("dados/index_perso_nivel", ordem=4)
        if not os.path.exists(self.arquivo):
            os.makedirs(os.path.dirname(self.arquivo), exist_ok=True)
            with open(self.arquivo, "wb") as f:
                f.write(struct.pack(self.header_fmt, 0))

    def create(self, personagem):
        with open(self.arquivo, "rb+") as f:
            f.seek(0)
            ultimo_id = struct.unpack(self.header_fmt, f.read(self.header_size))[0]
            novo_id = ultimo_id + 1
            personagem.id = novo_id
            primeiro_da_conta = self.hash_relacao.search(personagem.id_conta)
            f.seek(0, 2)
            posicao_atual = f.tell()
            personagem.prox = primeiro_da_conta if primeiro_da_conta is not None else -1
            f.write(personagem.to_bytes())
            self.hash_id.insert(novo_id, posicao_atual)
            try:
                self.arvore_id.inserir(novo_id, posicao_atual)
                self.arvore_nivel.inserir(int(personagem.nivel), posicao_atual)
            except Exception:
                pass
            self.hash_relacao.insert(personagem.id_conta, posicao_atual)
            f.seek(0)
            f.write(struct.pack(self.header_fmt, novo_id))
        funcao_str = personagem.funcao.decode('utf-8').strip('\x00')
        print(f"Personagem {novo_id} ({funcao_str}) criado com sucesso!")

    def read(self, id_alvo):
        pos = self.hash_id.search(id_alvo)
        if pos is not None:
            with open(self.arquivo, "rb") as f:
                f.seek(pos)
                dados = f.read(self.reg_size)
                if len(dados) == self.reg_size:
                    p = Personagem.from_bytes(dados)
                    if p.lapide == b' ':
                        return p
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
        pos = self.arvore_id.buscar(id_alvo)
        if pos is not None:
            with open(self.arquivo, "rb") as f:
                f.seek(pos)
                p = Personagem.from_bytes(f.read(self.reg_size))
                if p.lapide == b' ':
                    return p
        return None

    def listar_por_conta(self, id_conta_alvo):
        pos = self.hash_relacao.search(id_conta_alvo)
        if pos is None or pos == -1:
            return False
        with open(self.arquivo, "rb") as f:
            while pos != -1:
                f.seek(pos)
                dados = f.read(self.reg_size)
                if not dados:
                    break
                p = Personagem.from_bytes(dados)
                if p.lapide == b' ':
                    n_limpo = p.nome.decode('utf-8').strip('\x00')
                    f_limpa = p.funcao.decode('utf-8').strip('\x00')
                    print(f"{p.id:<5} | {n_limpo:<20} | {p.nivel:<10.2f} | {f_limpa:<10}")
                pos = p.prox
        return True

    def listar_todos_objetos(self):
        personagens = []
        with open(self.arquivo, "rb") as f:
            f.seek(self.header_size)
            while True:
                dados = f.read(self.reg_size)
                if len(dados) != self.reg_size:
                    break
                p = Personagem.from_bytes(dados)
                if p.lapide == b' ':
                    personagens.append(p)
        return personagens

    def buscar_por_nivel(self, nivel):
        pos = self.arvore_nivel.buscar(int(nivel))
        if pos is not None:
            with open(self.arquivo, "rb") as f:
                f.seek(pos)
                p = Personagem.from_bytes(f.read(self.reg_size))
                if p.lapide == b' ':
                    return [p]
        return []

    def update(self, id_alvo, novo_nome, novo_nivel, id_conta, nova_funcao):
        pos = self.hash_id.search(id_alvo)
        if pos is not None:
            with open(self.arquivo, "rb+") as f:
                f.seek(pos)
                p_antigo = Personagem.from_bytes(f.read(self.reg_size))
                f.seek(pos)
                p_novo = Personagem(id_alvo, novo_nome, novo_nivel, id_conta, nova_funcao)
                p_novo.prox = p_antigo.prox
                f.write(p_novo.to_bytes())
                return True
        return False

    def delete(self, id_alvo):
        pos = self.hash_id.search(id_alvo)
        if pos is not None:
            with open(self.arquivo, "rb+") as f:
                f.seek(pos)
                f.write(b'*')
            self.hash_id.remover(id_alvo)
            try:
                BairroDAO().remover_relacoes_por_personagem(id_alvo)
            except Exception:
                pass
            return True
        return False
