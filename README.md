# World of RPGcraft — Sistema de Personagens (AEDS III)

> Sistema de gerenciamento de personagens de RPG com indexação avançada (Hash Extensível,
> Árvore B+), relacionamentos 1:N e N:N, backup compactado (**Huffman** e **LZW**),
> **criptografia XOR** de senha e **busca textual por padrão** (**KMP** e **Boyer–Moore**).

O sistema possui **duas interfaces**: uma **Web** (navegador) e uma **CLI** (terminal).

---

## Requisitos

- Python 3.8+
- Nenhuma dependência externa necessária

---

## Interface Web

1. **Inicie o servidor:**

   ```bash
   python server.py
   ```

2. **Abra o navegador em:**

   ```
   http://localhost:8001
   ```

3. **Crie uma conta e faça login** (a senha é protegida por criptografia XOR).

Para encerrar o servidor, pressione `Ctrl + C` no terminal.

### Onde ver cada implementação na Web

| Implementação | Onde encontrar na interface |
|---|---|
| **Criptografia XOR** | Em **Criar Conta** e **Login** — a senha digitada é cifrada com XOR antes de ser salva no arquivo e nunca é exibida em texto claro. |
| **Busca por padrão (KMP / BM)** | Na página **Personagens**, no card **"Pesquisar por padrão (KMP / BM)"**: digite um trecho do nome, escolha o algoritmo (KMP ou Boyer–Moore) e clique em **Pesquisar**. |
| **Hash Extensível / Árvore B+** | Listagem de personagens e bairros (busca indexada por ID e por dono). |
| **Relacionamento N:N** | Página **Bairros** → adicionar/remover personagens de um bairro. |

### Passo a passo para testar a busca por padrão (Web)

1. Faça login e acesse **Personagens**.
2. Crie alguns personagens (ex.: *Arthas*, *Jaina*, *Artanis*).
3. No card **"Pesquisar por padrão (KMP / BM)"**, digite `art`.
4. Selecione **KMP** ou **Boyer–Moore** e clique em **Pesquisar**.
5. A tabela de resultados mostra os personagens cujo nome contém o padrão (busca *case-insensitive*).

---

## Interface CLI (Terminal)

1. **Execute o programa principal:**

   ```bash
   python main.py
   ```

2. **Funcionalidades por menu:**

   - **Login / Contas:** criar conta (com senha XOR), login, ordenação externa.
   - **Backup compactado (Huffman + LZW):** opção `7` do menu de contas — gera
     `backup_huffman.bin` e `backup_lzw.bin`.
   - **Personagens → opção `5` "Pesquisar por padrão (KMP / BM)":** escolha o algoritmo,
     informe o padrão e veja os registros encontrados.

---

## Estrutura do Projeto

| Caminho | Descrição |
|---|---|
| `server.py` | Servidor web (interface no navegador) |
| `main.py` | Interface de linha de comando (CLI) |
| `criptografia.py` | Funções de cifra XOR (`xor_cifrar`, `xor_decifrar`, `xor_verificar`) |
| `controller/CasamentoPadroes.py` | Algoritmos **KMP** e **Boyer–Moore** |
| `controller/HashExtensivel.py` | Índice Hash Extensível |
| `model/`, `dao/` | Modelos de dados e acesso aos arquivos binários |
| `backup.py` | Backup compactado (Huffman + LZW) |
| `Relatório/` | Documentação do trabalho (DOCX e PDF) |

---

## Ficheiros de Backup Gerados

| Ficheiro | Algoritmo | Descrição |
|---|---|---|
| `backup_huffman.bin` | Huffman | Backup compactado via codificação de Huffman |
| `backup_lzw.bin` | LZW | Backup compactado via algoritmo LZW |
