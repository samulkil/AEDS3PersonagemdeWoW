import struct
import os

class NodeBPlus:
    def __init__(self, eh_folha=True):
        self.eh_folha = eh_folha
        self.chaves = []
        self.ponteiros = [] # Em folhas, aponta para offsets do .bin. Em internos, para outros nós.
        self.proximo = -1   # Apenas para folhas (lista ligada entre folhas)

class ArvoreBPlus:
    def __init__(self, nome_arquivo, ordem=4):
        self.nome_arquivo = nome_arquivo + "_bplus.bin"
        self.ordem = ordem
        self.raiz = 0 # Offset da raiz no arquivo
        # Inicializar cabeçalho da árvore se arquivo não existir

    def buscar(self, chave):
        """Navega pelos nós internos até chegar na folha e encontrar a chave."""
        no_atual = self._ler_no(self.raiz)
        while not no_atual.eh_folha:
            # Encontra o caminho certo comparando chaves
            i = 0
            while i < len(no_atual.chaves) and chave >= no_atual.chaves[i]:
                i += 1
            no_atual = self._ler_no(no_atual.ponteiros[i])
        
        # Agora no_atual é uma folha, busca linear dentro dela
        for i, k in enumerate(no_atual.chaves):
            if k == chave:
                return no_atual.ponteiros[i] # Retorna offset do arquivo .bin
        return None

    def inserir(self, chave, endereco_bin):
        """Insere a chave na folha e realiza o Split se necessário."""
        # 1. Localiza a folha correta
        # 2. Insere a chave de forma ordenada
        # 3. Se len(chaves) == ordem: Split()
        # 4. Promove a chave do meio para o pai
        pass