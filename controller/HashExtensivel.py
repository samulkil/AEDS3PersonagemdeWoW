import struct

class HashExtensivel:
    def __init__(self, nome_arquivo, capacidade_bucket=4):
        self.nome_arq_diretorio = nome_arquivo + "_dir.bin"
        self.nome_arq_buckets = nome_arquivo + "_buckets.bin"
        self.capacidade = capacidade_bucket
        # Inicializar profundidade global e diretório se não existirem...

    def insert(self, chave, endereco):
                
        # 1. Calcula o hash da chave (ex: chave % (2**profundidade_global))
        # 2. Encontra o bucket correspondente
        # 3. Se houver espaço no bucket, insere (chave, endereco)
        # 4. Se não houver, realiza o "Split" (divisão) do bucket e aumenta a profundidade
        pass

    def search(self, chave):
        # 1. Calcula o hash
        # 2. Vai ao diretório -> encontra o bucket
        # 3. Procura a chave dentro do bucket e retorna o endereço (offset)
        pass