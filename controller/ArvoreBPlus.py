import struct
import os

class NodeBPlus:
    def __init__(self, eh_folha=True):
        self.eh_folha = eh_folha
        self.chaves = []
        self.ponteiros = []
        self.proximo = -1

class ArvoreBPlus:
    def __init__(self, nome_arquivo, ordem=4):
        self.nome_arquivo = nome_arquivo + "_bplus.bin"
        self.ordem = ordem
        self.raiz = 0

    def buscar(self, chave):
        """Navega pelos nós internos até chegar na folha e encontrar a chave."""
        no_atual = self._ler_no(self.raiz)
        while not no_atual.eh_folha:

            i = 0
            while i < len(no_atual.chaves) and chave >= no_atual.chaves[i]:
                i += 1
            no_atual = self._ler_no(no_atual.ponteiros[i])

        for i, k in enumerate(no_atual.chaves):
            if k == chave:
                return no_atual.ponteiros[i]
        return None

    def inserir(self, chave, endereco_bin):
        """Insere a chave na folha e realiza o Split se necessário."""

        pass