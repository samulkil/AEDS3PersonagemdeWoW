def _kmp_tabela_falha(padrao):
    tabela = [0] * len(padrao)
    k = 0
    for i in range(1, len(padrao)):
        while k > 0 and padrao[i] != padrao[k]:
            k = tabela[k - 1]
        if padrao[i] == padrao[k]:
            k += 1
        tabela[i] = k
    return tabela


def kmp_buscar(texto, padrao):
    ocorrencias = []
    n = len(texto)
    m = len(padrao)
    if m == 0 or n == 0 or m > n:
        return ocorrencias
    tabela = _kmp_tabela_falha(padrao)
    k = 0
    for i in range(n):
        while k > 0 and texto[i] != padrao[k]:
            k = tabela[k - 1]
        if texto[i] == padrao[k]:
            k += 1
        if k == m:
            ocorrencias.append(i - m + 1)
            k = tabela[k - 1]
    return ocorrencias


def _bm_tabela_bad_character(padrao):
    tabela = {}
    for i in range(len(padrao)):
        tabela[padrao[i]] = i
    return tabela


def _bm_tabela_good_suffix(padrao):
    m = len(padrao)
    deslocamento = [0] * (m + 1)
    borda = [0] * (m + 1)
    i = m
    j = m + 1
    borda[i] = j
    while i > 0:
        while j <= m and padrao[i - 1] != padrao[j - 1]:
            if deslocamento[j] == 0:
                deslocamento[j] = j - i
            j = borda[j]
        i -= 1
        j -= 1
        borda[i] = j
    j = borda[0]
    for i in range(m + 1):
        if deslocamento[i] == 0:
            deslocamento[i] = j
        if i == j:
            j = borda[j]
    return deslocamento


def boyer_moore_buscar(texto, padrao):
    ocorrencias = []
    n = len(texto)
    m = len(padrao)
    if m == 0 or n == 0 or m > n:
        return ocorrencias
    bad_character = _bm_tabela_bad_character(padrao)
    good_suffix = _bm_tabela_good_suffix(padrao)
    s = 0
    while s <= n - m:
        j = m - 1
        while j >= 0 and padrao[j] == texto[s + j]:
            j -= 1
        if j < 0:
            ocorrencias.append(s)
            s += good_suffix[0]
        else:
            desloc_bad = j - bad_character.get(texto[s + j], -1)
            desloc_good = good_suffix[j + 1]
            s += max(1, desloc_bad, desloc_good)
    return ocorrencias
