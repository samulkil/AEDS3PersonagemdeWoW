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
        if not bairros:
            with open(self.arquivo, "rb") as f:
                f.seek(self.header_size)
                while True:
                    dados = f.read(self.reg_size)
                    if len(dados) != self.reg_size:
                        break
                    b = Bairro.from_bytes(dados)
                    if b.lapide == b' ' and b.id_dono == id_dono:
                        bairros.append(b)
        bairros.sort(key=lambda b: b.id)
        return bairros

    def update(self, id_alvo, novo_nome, novo_id_dono):
        pos = self.arvore_id.buscar(id_alvo)
        if pos is None:
            with open(self.arquivo, "rb") as f:
                f.seek(self.header_size)
                offset = self.header_size
                while True:
                    dados = f.read(self.reg_size)
                    if len(dados) != self.reg_size:
                        break
                    b = Bairro.from_bytes(dados)
                    if b.id == id_alvo and b.lapide == b' ':
                        pos = offset
                        break
                    offset += self.reg_size
        if pos is None:
            return False
        with open(self.arquivo, "rb+") as f:
            f.seek(pos)
            b_antigo = Bairro.from_bytes(f.read(self.reg_size))
            if b_antigo.lapide != b' ':
                return False
            f.seek(pos)
            b_novo = Bairro(id_alvo, novo_nome, novo_id_dono)
            f.write(b_novo.to_bytes())
        try:
            self.arvore_dono.inserir(novo_id_dono, pos)
        except Exception:
            pass
        return True

    def delete(self, id_alvo):
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
        if self._relacao_existe(id_bairro, id_personagem):
            print("[Erro] Este personagem já está neste bairro!")
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
        pos = self.hash_relacao.search(id_bairro)
        if pos is None:
            print("[Erro] Bairro não possui personagens!")
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
        print("[Erro] Personagem não encontrado neste bairro!")
        return False

    def listar_personagens_do_bairro(self, id_bairro):
        pos = self.hash_relacao.search(id_bairro)
        if pos is None:
            print("[Aviso] Este bairro não possui personagens.")
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
