import struct
import os

class HashExtensivel:
    def __init__(self, nome_arquivo, capacidade_bucket=4):
        self.nome_arq_dir = nome_arquivo + "_dir.bin"
        self.nome_arq_buckets = nome_arquivo + "_buckets.bin"
        self.capacidade = capacidade_bucket
        
        self.fmt_bucket = "<ii" + ("iq" * self.capacidade)
        self.tam_bucket = struct.calcsize(self.fmt_bucket)

        if not self._arquivos_validos():
            self._inicializar_arquivos()

    def _inicializar_arquivos(self):
        """Cria o diretÃ³rio inicial e o primeiro bucket."""
        with open(self.nome_arq_buckets, "wb") as fb:
            vazio = [0, 0] + [0, 0] * self.capacidade
            fb.write(struct.pack(self.fmt_bucket, *vazio))
        
        with open(self.nome_arq_dir, "wb") as fd:
            fd.write(struct.pack("<i", 0))
            fd.write(struct.pack("<q", 0))

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
        """Calcula o Ã­ndice usando os bits menos significativos."""
        if isinstance(chave, str):
            return abs(hash(chave)) % (2 ** profundidade)
        elif isinstance(chave, bytes):
            return abs(hash(chave.decode('utf-8'))) % (2 ** profundidade)
        return chave % (2 ** profundidade)
    
    def _normalizar_chave(self, chave):
        """Converte a chave para formato hashÃ¡vel."""
        if isinstance(chave, str):
            return chave
        elif isinstance(chave, bytes):
            return chave.decode('utf-8')
        return chave

    def search(self, chave):
        """Realiza a busca direta por uma chave."""
        if not os.path.exists(self.nome_arq_dir): return None

        if isinstance(chave, str):
            chave_busca = abs(hash(chave)) % (2**31)
        else:
            chave_busca = chave

        with open(self.nome_arq_dir, "rb") as fd, open(self.nome_arq_buckets, "rb") as fb:
            prof_global = self._get_prof_global(fd)
            indice_dir = self._hash(chave, prof_global)
            
            fd.seek(4 + indice_dir * 8)
            end_bucket = struct.unpack("<q", fd.read(8))[0]
            
            fb.seek(end_bucket)
            dados = struct.unpack(self.fmt_bucket, fb.read(self.tam_bucket))
            
            qtd = dados[1]
            conteudo = dados[2:]
            
            for i in range(0, qtd * 2, 2):
                chave_bucket = conteudo[i]
                if isinstance(chave, str):
                    if abs(hash(chave)) % (2**31) == chave_bucket:
                        return conteudo[i+1]
                elif chave_bucket == chave_busca:
                    return conteudo[i+1]
        return None

    def insert(self, chave, endereco_bin):
        """Insere uma nova chave ou atualiza o endereÃ§o se a chave jÃ¡ existir."""
        if isinstance(chave, str):
            chave_num = abs(hash(chave)) % (2**31)
        else:
            chave_num = chave
            
        with open(self.nome_arq_dir, "rb+") as fd, open(self.nome_arq_buckets, "rb+") as fb:
            prof_global = self._get_prof_global(fd)
            indice_dir = self._hash(chave, prof_global)
            
            fd.seek(4 + indice_dir * 8)
            end_bucket = struct.unpack("<q", fd.read(8))[0]
            
            fb.seek(end_bucket)
            dados = list(struct.unpack(self.fmt_bucket, fb.read(self.tam_bucket)))
            prof_local, qtd = dados[0], dados[1]
            conteudo = dados[2:]

            for i in range(0, qtd * 2, 2):
                chave_bucket = conteudo[i]
                if isinstance(chave, str):
                    if hash(chave) == chave_bucket:
                        dados[2 + i + 1] = endereco_bin 
                        fb.seek(end_bucket)
                        fb.write(struct.pack(self.fmt_bucket, *dados))
                        fb.flush()
                        return True
                elif chave_bucket == chave_num:
                    dados[2 + i + 1] = endereco_bin 
                    fb.seek(end_bucket)
                    fb.write(struct.pack(self.fmt_bucket, *dados))
                    fb.flush()
                    return True

            if qtd < self.capacidade:
                dados[2 + qtd*2] = chave_num
                dados[2 + qtd*2 + 1] = endereco_bin
                dados[1] += 1
                fb.seek(end_bucket)
                fb.write(struct.pack(self.fmt_bucket, *dados))
                fb.flush()
                return True
            
            else:
                if prof_local == prof_global:
                    self._duplicar_diretorio(fd)
                    prof_global += 1
                
                self._split_bucket(fb, fd, end_bucket, prof_global)
                return self.insert(chave, endereco_bin)

    def _duplicar_diretorio(self, fd):
        """Dobra o tamanho do diretÃ³rio no disco."""
        fd.seek(0)
        prof_global = struct.unpack("<i", fd.read(4))[0]
        
        enderecos = []
        for _ in range(2**prof_global):
            enderecos.append(struct.unpack("<q", fd.read(8))[0])
            
        fd.seek(0)
        fd.write(struct.pack("<i", prof_global + 1))
        for end in enderecos + enderecos:
            fd.write(struct.pack("<q", end))
        fd.flush()

    def _split_bucket(self, fb, fd, end_bucket_antigo, prof_global):
        """Divide um bucket cheio em dois e redistribui as chaves."""
        fb.seek(end_bucket_antigo)
        dados_antigos = list(struct.unpack(self.fmt_bucket, fb.read(self.tam_bucket)))
        prof_local_nova = dados_antigos[0] + 1
        chaves_para_reindexar = []
        
        for i in range(0, dados_antigos[1] * 2, 2):
            chaves_para_reindexar.append((dados_antigos[2+i], dados_antigos[2+i+1]))
            
        vazio = [prof_local_nova, 0] + [0, 0] * self.capacidade
        fb.seek(end_bucket_antigo)
        fb.write(struct.pack(self.fmt_bucket, *vazio))
        fb.flush()
        
        fb.seek(0, 2)
        end_bucket_novo = fb.tell()
        fb.write(struct.pack(self.fmt_bucket, *vazio))
        fb.flush()
        
        bit_novo = 1 << (prof_local_nova - 1)
        for i in range(2**prof_global):
            if (i & bit_novo) != 0:
                fd.seek(4 + i * 8)
                if struct.unpack("<q", fd.read(8))[0] == end_bucket_antigo:
                    fd.seek(4 + i * 8)
                    fd.write(struct.pack("<q", end_bucket_novo))
        fd.flush()
        
        for c, e in chaves_para_reindexar:
            self.insert(c, e)

    def remover(self, chave):
        """Remove uma chave do hash."""
        if not os.path.exists(self.nome_arq_dir): return False

        if isinstance(chave, str):
            chave_num = abs(hash(chave)) % (2**31)
        else:
            chave_num = chave

        with open(self.nome_arq_dir, "rb+") as fd, open(self.nome_arq_buckets, "rb+") as fb:
            prof_global = self._get_prof_global(fd)
            indice_dir = self._hash(chave, prof_global)
            
            fd.seek(4 + indice_dir * 8)
            end_bucket = struct.unpack("<q", fd.read(8))[0]
            
            fb.seek(end_bucket)
            dados = list(struct.unpack(self.fmt_bucket, fb.read(self.tam_bucket)))
            
            prof_local = dados[0]
            qtd = dados[1]
            conteudo = dados[2:]
            
            for i in range(0, qtd * 2, 2):
                chave_bucket = conteudo[i]
                if isinstance(chave, str):
                    if abs(hash(chave)) % (2**31) == chave_bucket:
                        nova_qtd = qtd - 1
                        novo_conteudo = []
                        
                        for j in range(0, qtd * 2, 2):
                            if j != i:
                                novo_conteudo.append(conteudo[j])
                                novo_conteudo.append(conteudo[j+1])
                        
                        while len(novo_conteudo) < self.capacidade * 2:
                            novo_conteudo.append(0)
                            novo_conteudo.append(0)
                        
                        dados_atualizados = [prof_local, nova_qtd] + novo_conteudo
                        fb.seek(end_bucket)
                        fb.write(struct.pack(self.fmt_bucket, *dados_atualizados))
                        fb.flush()
                        return True
                elif chave_bucket == chave_num:
                    nova_qtd = qtd - 1
                    novo_conteudo = []
                    
                    for j in range(0, qtd * 2, 2):
                        if j != i:
                            novo_conteudo.append(conteudo[j])
                            novo_conteudo.append(conteudo[j+1])
                    
                    while len(novo_conteudo) < self.capacidade * 2:
                        novo_conteudo.append(0)
                        novo_conteudo.append(0)
                    
                    dados_atualizados = [prof_local, nova_qtd] + novo_conteudo
                    fb.seek(end_bucket)
                    fb.write(struct.pack(self.fmt_bucket, *dados_atualizados))
                    fb.flush()
                    return True
            
        return False