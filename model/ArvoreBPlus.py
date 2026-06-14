import struct
import os

class NodeBPlus:
    def __init__(self, eh_folha=True):
        self.eh_folha = eh_folha
        self.chaves = []
        self.ponteiros = []
        self.proximo = -1
        self.offset = None

class ArvoreBPlus:
    def __init__(self, nome_arquivo, ordem=4):
        self.nome_arquivo = nome_arquivo
        self.ordem = ordem
        self.max_chaves = ordem - 1

        self.formato = "<ii" + "i"*self.max_chaves + "q"*ordem + "q"
        self.tam_no = struct.calcsize(self.formato)

        if not os.path.exists(self.nome_arquivo):
            self._inicializar()

    def _inicializar(self):
        with open(self.nome_arquivo, "wb") as f:
            f.write(struct.pack("<q", -1))

            raiz = NodeBPlus(True)
            offset = self._escrever_no(raiz, f)

            f.seek(0)
            f.write(struct.pack("<q", offset))

    def _ler_raiz(self):
        with open(self.nome_arquivo, "rb") as f:
            return struct.unpack("<q", f.read(8))[0]

    def _escrever_raiz(self, offset):
        with open(self.nome_arquivo, "rb+") as f:
            f.seek(0)
            f.write(struct.pack("<q", offset))

    def _escrever_no(self, no, f=None):
        close = False
        if f is None:
            f = open(self.nome_arquivo, "rb+")
            close = True

        if no.offset is None:
            f.seek(0, 2)
            no.offset = f.tell()
        else:
            f.seek(no.offset)

        chaves = no.chaves + [0]*(self.max_chaves - len(no.chaves))
        ponteiros = no.ponteiros + [0]*(self.ordem - len(no.ponteiros))

        dados = struct.pack(
            self.formato,
            int(no.eh_folha),
            len(no.chaves),
            *chaves,
            *ponteiros,
            no.proximo
        )

        f.write(dados)

        if close:
            f.close()

        return no.offset

    def _ler_no(self, offset):
        with open(self.nome_arquivo, "rb") as f:
            f.seek(offset)
            dados = struct.unpack(self.formato, f.read(self.tam_no))

        eh_folha = dados[0]
        qtd = dados[1]

        chaves = list(dados[2:2+self.max_chaves])[:qtd]
        ponteiros = list(dados[2+self.max_chaves:2+self.max_chaves+self.ordem])

        no = NodeBPlus(bool(eh_folha))
        no.chaves = chaves

        if eh_folha:
            no.ponteiros = ponteiros[:qtd]
        else:
            no.ponteiros = ponteiros[:qtd+1]

        no.proximo = dados[-1]
        no.offset = offset

        return no

    def buscar(self, chave):
        no = self._ler_no(self._ler_raiz())

        while not no.eh_folha:
            i = 0
            while i < len(no.chaves) and chave >= no.chaves[i]:
                i += 1
            no = self._ler_no(no.ponteiros[i])

        for i, k in enumerate(no.chaves):
            if k == chave:
                return no.ponteiros[i]

        return None

    def buscar_todos(self, chave):
        resultados = []

        no = self._ler_no(self._ler_raiz())

        while not no.eh_folha:
            i = 0
            while i < len(no.chaves) and chave >= no.chaves[i]:
                i += 1
            no = self._ler_no(no.ponteiros[i])

        while True:
            for i, k in enumerate(no.chaves):
                if k == chave:
                    resultados.append(no.ponteiros[i])

            if no.proximo == -1:
                break

            no = self._ler_no(no.proximo)

        return resultados

    def inserir(self, chave, valor):
        raiz = self._ler_no(self._ler_raiz())

        caminho = []
        no = raiz

        while not no.eh_folha:
            i = 0
            while i < len(no.chaves) and chave >= no.chaves[i]:
                i += 1
            caminho.append((no, i))
            no = self._ler_no(no.ponteiros[i])

        self._inserir_em_folha(no, chave, valor)

        self._resolver_split(no, caminho)

    def _inserir_em_folha(self, no, chave, valor):
        i = 0
        while i < len(no.chaves) and chave > no.chaves[i]:
            i += 1

        no.chaves.insert(i, chave)
        no.ponteiros.insert(i, valor)

    def _resolver_split(self, no, caminho):
        while True:
            if len(no.chaves) <= self.max_chaves:
                self._escrever_no(no)
                return

            if no.eh_folha:
                chave_subir, novo = self._split_folha(no)
            else:
                chave_subir, novo = self._split_interno(no)

            if not caminho:

                nova_raiz = NodeBPlus(False)
                nova_raiz.chaves = [chave_subir]
                nova_raiz.ponteiros = [no.offset, novo.offset]

                offset = self._escrever_no(nova_raiz)
                self._escrever_raiz(offset)
                return

            pai, idx = caminho.pop()

            pai.chaves.insert(idx, chave_subir)
            pai.ponteiros.insert(idx+1, novo.offset)

            no = pai

    def _split_folha(self, no):
        meio = len(no.chaves) // 2

        novo = NodeBPlus(True)

        novo.chaves = no.chaves[meio:]
        novo.ponteiros = no.ponteiros[meio:]

        no.chaves = no.chaves[:meio]
        no.ponteiros = no.ponteiros[:meio]

        novo.proximo = no.proximo
        self._escrever_no(novo)

        no.proximo = novo.offset
        self._escrever_no(no)

        return novo.chaves[0], novo

    def _split_interno(self, no):
        meio = len(no.chaves) // 2

        chave_subir = no.chaves[meio]

        novo = NodeBPlus(False)

        novo.chaves = no.chaves[meio+1:]
        novo.ponteiros = no.ponteiros[meio+1:]

        no.chaves = no.chaves[:meio]
        no.ponteiros = no.ponteiros[:meio+1]

        self._escrever_no(novo)
        self._escrever_no(no)

        return chave_subir, novo