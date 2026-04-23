import struct
import os

class HashExtensivel:
    def __init__(self, nome_arquivo, capacidade_bucket=4):
        # Nomes dos arquivos de índice
        self.nome_arq_dir = nome_arquivo + "_dir.bin"
        self.nome_arq_buckets = nome_arquivo + "_buckets.bin"
        self.capacidade = capacidade_bucket
        
        # Formato do Bucket: Profundidade Local (i), Quantidade (i), 
        # seguido por N pares de (Chave Inteira (i), Endereço Long Long (q))
        self.fmt_bucket = "<ii" + ("iq" * self.capacidade)
        self.tam_bucket = struct.calcsize(self.fmt_bucket)

<<<<<<< Updated upstream
        # Inicializa os arquivos se não existirem
        if not os.path.exists(self.nome_arq_dir):
=======
        if not self._arquivos_validos():
>>>>>>> Stashed changes
            self._inicializar_arquivos()

    def _inicializar_arquivos(self):
        """Cria o diretório inicial e o primeiro bucket."""
        # 1. Cria o primeiro bucket (profundidade local 0, 0 registros)
        with open(self.nome_arq_buckets, "wb") as fb:
            # Lista: [prof_local, qtd, chave1, end1, chave2, end2...]
            vazio = [0, 0] + [0, 0] * self.capacidade
            fb.write(struct.pack(self.fmt_bucket, *vazio))
        
        # 2. Cria o diretório (profundidade global 0, aponta para bucket no offset 0)
        with open(self.nome_arq_dir, "wb") as fd:
            fd.write(struct.pack("<i", 0)) # Profundidade Global
            fd.write(struct.pack("<q", 0)) # Endereço do Bucket 0

    def _arquivos_validos(self):
        if not os.path.exists(self.nome_arq_dir) or not os.path.exists(self.nome_arq_buckets):
            return False

        try:
            with open(self.nome_arq_dir, "rb") as fd:
                header = fd.read(4)
                if len(header) != 4:
                    return False
                prof_global = struct.unpack("<i", header)[0]
                expected_dir_size = 4 + 8 * (2 ** prof_global)
                if os.path.getsize(self.nome_arq_dir) != expected_dir_size:
                    return False

                offsets = []
                for _ in range(2 ** prof_global):
                    off_data = fd.read(8)
                    if len(off_data) != 8:
                        return False
                    offsets.append(struct.unpack("<q", off_data)[0])

            bucket_size = os.path.getsize(self.nome_arq_buckets)
            if bucket_size < self.tam_bucket or bucket_size % self.tam_bucket != 0:
                return False

            for offset in offsets:
                if offset < 0 or offset + self.tam_bucket > bucket_size or offset % self.tam_bucket != 0:
                    return False
        except Exception:
            return False

        return True

    def _get_prof_global(self, fd):
        fd.seek(0)
        return struct.unpack("<i", fd.read(4))[0]

    def _hash(self, chave, profundidade):
        """Calcula o índice usando os bits menos significativos."""
        return chave % (2 ** profundidade)

    def search(self, chave):
        """Realiza a busca direta por uma chave."""
        if not os.path.exists(self.nome_arq_dir): return None

        with open(self.nome_arq_dir, "rb") as fd, open(self.nome_arq_buckets, "rb") as fb:
            prof_global = self._get_prof_global(fd)
            indice_dir = self._hash(chave, prof_global)
            
            # Localiza o endereço do bucket no diretório
            fd.seek(4 + indice_dir * 8)
            end_bucket = struct.unpack("<q", fd.read(8))[0]
            
            # Lê o conteúdo do bucket
            fb.seek(end_bucket)
            dados = struct.unpack(self.fmt_bucket, fb.read(self.tam_bucket))
            
            qtd = dados[1]
            conteudo = dados[2:]
            
            # Procura a chave dentro do bucket
            for i in range(0, qtd * 2, 2):
                if conteudo[i] == chave:
                    return conteudo[i+1] # Retorna o offset no arquivo .bin principal
        return None

    def insert(self, chave, endereco_bin):
        """Insere uma nova chave e seu endereço no índice."""
        with open(self.nome_arq_dir, "rb+") as fd, open(self.nome_arq_buckets, "rb+") as fb:
            prof_global = self._get_prof_global(fd)
            indice_dir = self._hash(chave, prof_global)
            
            fd.seek(4 + indice_dir * 8)
            end_bucket = struct.unpack("<q", fd.read(8))[0]
            
            fb.seek(end_bucket)
            dados = list(struct.unpack(self.fmt_bucket, fb.read(self.tam_bucket)))
            prof_local, qtd = dados[0], dados[1]
<<<<<<< Updated upstream
=======
            conteudo = dados[2:]

            # --- CORREÇÃO: Atualiza se a chave já existe (importante para o 1:N) ---
            for i in range(0, qtd * 2, 2):
                if conteudo[i] == chave:
                    dados[2 + i + 1] = endereco_bin 
                    fb.seek(end_bucket)
                    fb.write(struct.pack(self.fmt_bucket, *dados))
                    fb.flush()
                    return True
>>>>>>> Stashed changes

            # Caso 1: Ainda há espaço no bucket
            if qtd < self.capacidade:
                dados[2 + qtd*2] = chave
                dados[2 + qtd*2 + 1] = endereco_bin
                dados[1] += 1
                fb.seek(end_bucket)
                fb.write(struct.pack(self.fmt_bucket, *dados))
                fb.flush()
                return True
            
            # Caso 2: Bucket cheio, precisa de Split (Divisão)
            else:
                if prof_local == prof_global:
                    self._duplicar_diretorio(fd)
                    prof_global += 1
                
                self._split_bucket(fb, fd, end_bucket, prof_global)
                # Tenta inserir novamente após a redistribuição
                return self.insert(chave, endereco_bin)

    def _duplicar_diretorio(self, fd):
        """Dobra o tamanho do diretório quando prof_local == prof_global."""
        fd.seek(0)
        prof_global = struct.unpack("<i", fd.read(4))[0]
        
<<<<<<< Updated upstream
        fd.seek(4)
        enderecos_atuais = [struct.unpack("<q", fd.read(8))[0] for _ in range(2**prof_global)]
        
        # O novo diretório é o dobro, espelhando os endere
=======
        enderecos = []
        for _ in range(2**prof_global):
            enderecos.append(struct.unpack("<q", fd.read(8))[0])
            
        fd.seek(0)
        fd.write(struct.pack("<i", prof_global + 1))
        # O novo diretório contém duas cópias dos endereços antigos
        for end in enderecos + enderecos:
            fd.write(struct.pack("<q", end))
        fd.flush()

    def _split_bucket(self, fb, fd, end_bucket_antigo, prof_global):
        """Divide um bucket cheio em dois e redistribui as chaves."""
        fb.seek(end_bucket_antigo)
        dados_antigos = list(struct.unpack(self.fmt_bucket, fb.read(self.tam_bucket)))
        prof_local_nova = dados_antigos[0] + 1
        chaves_para_reindexar = []
        
        # Extrai chaves e endereços do bucket cheio
        for i in range(0, dados_antigos[1] * 2, 2):
            chaves_para_reindexar.append((dados_antigos[2+i], dados_antigos[2+i+1]))
            
        # Limpa o bucket antigo e atualiza profundidade local
        vazio = [prof_local_nova, 0] + [0, 0] * self.capacidade
        fb.seek(end_bucket_antigo)
        fb.write(struct.pack(self.fmt_bucket, *vazio))
        fb.flush()
        
        # Cria o novo bucket no fim do arquivo
        fb.seek(0, 2)
        end_bucket_novo = fb.tell()
        fb.write(struct.pack(self.fmt_bucket, *vazio))
        fb.flush()
        
        # Atualiza o diretório para apontar para o novo bucket
        # Apenas as entradas que terminam com o novo bit de hash devem ser atualizadas
        bit_novo = 1 << (prof_local_nova - 1)
        for i in range(2**prof_global):
            if (i & bit_novo) != 0:
                # Se o índice do diretório apontava para o bucket antigo, 
                # e agora tem o bit novo ativado, aponta para o novo bucket
                fd.seek(4 + i * 8)
                if struct.unpack("<q", fd.read(8))[0] == end_bucket_antigo:
                    fd.seek(4 + i * 8)
                    fd.write(struct.pack("<q", end_bucket_novo))
        fd.flush()
        
        # Redistribui as chaves entre os dois buckets
        for c, e in chaves_para_reindexar:
            self.insert(c, e)
>>>>>>> Stashed changes
