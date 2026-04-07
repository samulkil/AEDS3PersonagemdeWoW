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

        # Inicializa os arquivos se não existirem
        if not os.path.exists(self.nome_arq_dir):
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

            # Caso 1: Ainda há espaço no bucket
            if qtd < self.capacidade:
                dados[2 + qtd*2] = chave
                dados[2 + qtd*2 + 1] = endereco_bin
                dados[1] += 1
                fb.seek(end_bucket)
                fb.write(struct.pack(self.fmt_bucket, *dados))
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
        
        fd.seek(4)
        enderecos_atuais = [struct.unpack("<q", fd.read(8))[0] for _ in range(2**prof_global)]
        
        # O novo diretório é o dobro, espelhando os endere