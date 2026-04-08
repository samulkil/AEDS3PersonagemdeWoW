import struct
import os
from model.Conta import Conta
from controller.HashExtensivel import HashExtensivel
from controller.ArvoreBPlus import ArvoreBPlus

class ContaDAO:
    def __init__(self, arquivo="dados/contas.bin"):
        self.arquivo = arquivo
        self.header_fmt = "<i"
        self.header_size = struct.calcsize(self.header_fmt)
        self.reg_size = struct.calcsize(Conta.FORMATO)
        self.hash = HashExtensivel("dados/index_contas")
        self.bplus = ArvoreBPlus("dados/index_contas")
        
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
            self.bplus.inserir(novo_id, pos)

            f.seek(0)
            f.write(struct.pack(self.header_fmt, novo_id))
            print(f"Conta do usuário {novo_id} criada com sucesso!")

    def read(self, id_alvo):
        posicao = self.hash.search(id_alvo)
        if posicao is not None:
            with open(self.arquivo, "rb") as f:
                f.seek(posicao)
                dados = f.read(self.reg_size)
                if not dados: return None
                
                conta = Conta.from_bytes(dados)
                # O Hash encontrou o registro, agora só conferimos a lápide
                if conta.lapide == b' ':
                    return conta
        return None

    def read_por_usuario(self, nome_usuario):
        with open(self.arquivo, "rb") as f:
            f.seek(self.header_size)
            while True:
                posicao_atual = f.tell()
                lapide = f.read(1)
                if not lapide: break
                
                dados = f.read(self.reg_size - 1)
                usuario_lido = struct.unpack("<20s", dados[4:24])[0]
                usuario_limpo = usuario_lido.decode('utf-8').strip('\x00')

                if usuario_limpo == nome_usuario and lapide == b' ':
                    f.seek(posicao_atual)
                    return Conta.from_bytes(f.read(self.reg_size))
        return None
    
    def update(self, id_alvo, conta_atualizada):
        pos = self.hash.search(id_alvo)
        if pos is not None: # Verifica se a posição foi encontrada
            with open(self.arquivo, "rb+") as f:
                f.seek(pos) # VAI PARA A POSIÇÃO CORRETA INDICADA PELO HASH
                # Escreve os novos bytes da conta diretamente por cima dos antigos
                f.write(conta_atualizada.to_bytes())
                return True
        return False
    
    def delete(self, id_alvo):
        posicao = self.hash.search(id_alvo)
        if posicao is not None:
            with open(self.arquivo, "rb+") as f:
                f.seek(posicao) # Pula direto para o registro
                f.write(b'*')   # Marca a lápide na primeira posição do registro
                print(f"Conta ID {id_alvo} excluída com sucesso!")
                return True
        return False

    import os

    def ordenar_externo_usuario(self):
    # Configurações: Tamanho do bloco (ex: 3 registros por vez)
        TAM_BLOCO = 3
        runs = []
    
        # --- ETAPA 1: DISTRIBUIÇÃO (Criação dos Runs) ---
        with open(self.arquivo, "rb") as f:
            f.seek(self.header_size)
            contador_run = 0
        
            while True:
                bloco = []
                for _ in range(TAM_BLOCO):
                    dados = f.read(self.reg_size)
                    if not dados: break
                    c = Conta.from_bytes(dados)
                    if c.lapide == b' ': # Apenas registros ativos
                        bloco.append(c)
            
                if not bloco: break
            
                # Ordena o bloco na RAM
                bloco.sort(key=lambda x: x.usuario.decode('utf-8').strip('\x00').lower())
            
                # Grava o Run em disco
                nome_run = f"dados/run_{contador_run}.bin"
                with open(nome_run, "wb") as f_run:
                    for c in bloco:
                        f_run.write(c.to_bytes())
            
                runs.append(nome_run)
                contador_run += 1

        # --- ETAPA 2: INTERCALAÇÃO (Merge) ---
        if not runs: return
    
        arquivo_final = "dados/contas_ordenadas.bin"
        # Abre todos os runs simultaneamente
        fps = [open(r, "rb") for r in runs]
    
        with open(arquivo_final, "wb") as f_out:
            # Lista para manter o registro atual de cada run
            buffer = []
            for fp in fps:
                dados = fp.read(self.reg_size)
                if dados:
                    buffer.append(Conta.from_bytes(dados))
                else:
                    buffer.append(None)

            while any(c is not None for c in buffer):
                # Encontra o menor usuário entre os buffers ativos
                menor_idx = -1
                for i, c in enumerate(buffer):
                    if c is not None:
                        if menor_idx == -1 or c.usuario < buffer[menor_idx].usuario:
                            menor_idx = i
            
                # Escreve o menor no arquivo final
                f_out.write(buffer[menor_idx].to_bytes())
            
                # Repõe o buffer do run que foi usado
                proximo_dados = fps[menor_idx].read(self.reg_size)
                if proximo_dados:
                    buffer[menor_idx] = Conta.from_bytes(proximo_dados)
                else:
                    buffer[menor_idx] = None

        # Fecha e limpa os arquivos temporários
        for fp in fps: fp.close()
        for r in runs: os.remove(r)
    
        print(f"\n[SUCESSO] Arquivo '{arquivo_final}' gerado com sucesso!")