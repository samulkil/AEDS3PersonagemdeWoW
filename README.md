# Sistema de Backup Compactado

> Ferramenta de backup com compressão usando os algoritmos **Huffman** e **LZW**.

---

## Como Testar

1. **Execute o programa principal:**

   ```bash
   python main.py
   ```

2. **No menu principal, escolha a opção de backup:**

   - Selecione a opção `7` para **Fazer Backup Compactado (Huffman + LZW)**.

3. **Aguarde a mensagem de sucesso:** O programa deve informar os caminhos de:

   - `backup_huffman.bin`
   - `backup_lzw.bin`

4. **Verifique os ficheiros gerados:** Confira no seu diretório se os ficheiros foram criados corretamente:

   - `backup_huffman.bin`
   - `backup_lzw.bin`

---

## Requisitos

- Python 3.8+
- Nenhuma dependência externa necessária

## Estrutura dos Ficheiros de Saída

| Ficheiro | Algoritmo | Descrição |
|---|---|---|
| `backup_huffman.bin` | Huffman | Backup compactado via codificação de Huffman |
| `backup_lzw.bin` | LZW | Backup compactado via algoritmo LZW |
