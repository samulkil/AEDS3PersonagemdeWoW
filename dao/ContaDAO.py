import struct
import os
from model.Conta import Conta
from controller.HashExtensivel import HashExtensivel

class ContaDAO:
    def __init__(self, arquivo="dados/contas.bin"):
        self.arquivo = arquivo
        self.header_fmt = "<i"
        self.header_size = struct.calcsize(self.header_fmt)
        self.reg_size = struct.calcsize(Conta.FORMATO)
        self.hash = HashExtensivel("dados/index_contas")
        self.hash_usuario = HashExtensivel("dados/index_contas_usuario")
        if not os.path.exists(self.arquivo):
            os.makedirs(os.path.dirname(self.arquivo), exist_ok=True)
            with open(self.arquivo, "wb") as f:
                f.write(struct.pack(self.header_fmt, 0))

    def create(self, conta):
        with open(self.arquivo, "rb+") as f:
            f.seek(0)
            ultimo_id = struct.unpack(self.header_fmt, f.read(self.header_size))[0]
            novo_id = ultimo_id + 1
            conta.id = novo_id
            f.seek(0, 2)
            pos = f.tell()
            f.write(conta.to_bytes())
            self.hash.insert(novo_id, pos)
            nome_usuario = conta.usuario.decode('utf-8').strip('\x00')
            self.hash_usuario.insert(nome_usuario, pos)
            f.seek(0)
            f.write(struct.pack(self.header_fmt, novo_id))
            print(f"Conta do usuário {novo_id} criada com sucesso!")

    def read(self, id_alvo):
        posicao = self.hash.search(id_alvo)
        if posicao is not None:
            with open(self.arquivo, "rb") as f:
                f.seek(posicao)
                dados = f.read(self.reg_size)
                if not dados:
                    return None
                conta = Conta.from_bytes(dados)
                if conta.lapide == b' ':
                    return conta
        return None

    def read_por_usuario(self, nome_usuario):
        posicao = self.hash_usuario.search(nome_usuario)
        if posicao is not None:
            with open(self.arquivo, "rb") as f:
                f.seek(posicao)
                dados = f.read(self.reg_size)
                if not dados:
                    return None
                conta = Conta.from_bytes(dados)
                if conta.lapide == b' ':
                    return conta
        return None

    def update(self, id_alvo, conta_atualizada):
        pos = self.hash.search(id_alvo)
        if pos is not None:
            with open(self.arquivo, "rb") as f:
                f.seek(pos)
                dados = f.read(self.reg_size)
                conta_antiga = Conta.from_bytes(dados)
                nome_antigo = conta_antiga.usuario.decode('utf-8').strip('\x00')
            with open(self.arquivo, "rb+") as f:
                f.seek(pos)
                f.write(conta_atualizada.to_bytes())
            self.hash.insert(id_alvo, pos)
            nome_novo = conta_atualizada.usuario.decode('utf-8').strip('\x00')
            if nome_antigo != nome_novo:
                self.hash_usuario.remover(nome_antigo)
                self.hash_usuario.insert(nome_novo, pos)
            return True
        return False

    def delete(self, id_alvo):
        posicao = self.hash.search(id_alvo)
        if posicao is not None:
            with open(self.arquivo, "rb") as f:
                f.seek(posicao)
                dados = f.read(self.reg_size)
                conta = Conta.from_bytes(dados)
                nome_usuario = conta.usuario.decode('utf-8').strip('\x00')
            with open(self.arquivo, "rb+") as f:
                f.seek(posicao)
                f.write(b'*')
            self.hash.remover(id_alvo)
            self.hash_usuario.remover(nome_usuario)
            print(f"Conta ID {id_alvo} excluída com sucesso!")
            return True
        return False

    def ordenar_externo_usuario(self):
        TAM_BLOCO = 3
        runs = []
        with open(self.arquivo, "rb") as f:
            f.seek(self.header_size)
            contador_run = 0
            while True:
                bloco = []
                for _ in range(TAM_BLOCO):
                    dados = f.read(self.reg_size)
                    if not dados:
                        break
                    c = Conta.from_bytes(dados)
                    if c.lapide == b' ':
                        bloco.append(c)
                if not bloco:
                    break
                bloco.sort(key=lambda x: x.usuario.decode('utf-8').strip('\x00').lower())
                nome_run = f"dados/run_{contador_run}.bin"
                with open(nome_run, "wb") as f_run:
                    for c in bloco:
                        f_run.write(c.to_bytes())
                runs.append(nome_run)
                contador_run += 1
        if not runs:
            return
        arquivo_final = "dados/contas_ordenadas.bin"
        fps = [open(r, "rb") for r in runs]
        with open(arquivo_final, "wb") as f_out:
            buffer = []
            for fp in fps:
                dados = fp.read(self.reg_size)
                if dados:
                    buffer.append(Conta.from_bytes(dados))
                else:
                    buffer.append(None)
            while any(c is not None for c in buffer):
                menor_idx = -1
                for i, c in enumerate(buffer):
                    if c is not None:
                        if menor_idx == -1 or c.usuario < buffer[menor_idx].usuario:
                            menor_idx = i
                f_out.write(buffer[menor_idx].to_bytes())
                proximo_dados = fps[menor_idx].read(self.reg_size)
                if proximo_dados:
                    buffer[menor_idx] = Conta.from_bytes(proximo_dados)
                else:
                    buffer[menor_idx] = None
        for fp in fps:
            fp.close()
        for r in runs:
            os.remove(r)
        print(f"\n[SUCESSO] Arquivo '{arquivo_final}' gerado com sucesso!")
