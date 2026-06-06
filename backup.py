import os
import struct
import heapq

ARCHIVE_MAGIC = b'AEDSBKUP'
ARCHIVE_VERSION = 1
ALGO_HUFFMAN = 1
ALGO_LZW = 2


def _gather_data_files(dados_dir='dados'):
    arquivos = []
    for root, _, files in os.walk(dados_dir):
        for nome in sorted(files):
            caminho = os.path.join(root, nome)
            rel_path = os.path.relpath(caminho, dados_dir)
            arquivos.append((caminho, rel_path))
    return arquivos


class _HuffmanNode:
    def __init__(self, freq, byte=None, left=None, right=None):
        self.freq = freq
        self.byte = byte
        self.left = left
        self.right = right

    def __lt__(self, other):
        return self.freq < other.freq


def _build_huffman_codes(freq_table):
    heap = []
    for b, freq in enumerate(freq_table):
        if freq > 0:
            heapq.heappush(heap, _HuffmanNode(freq, byte=b))

    if not heap:
        return {0: '0'}

    if len(heap) == 1:
        node = heapq.heappop(heap)
        heapq.heappush(heap, _HuffmanNode(node.freq, None, left=node, right=_HuffmanNode(0, byte=node.byte)))

    while len(heap) > 1:
        left = heapq.heappop(heap)
        right = heapq.heappop(heap)
        merged = _HuffmanNode(left.freq + right.freq, None, left=left, right=right)
        heapq.heappush(heap, merged)

    root = heapq.heappop(heap)
    codes = {}

    def _walk(node, prefix=''):
        if node.byte is not None:
            codes[node.byte] = prefix or '0'
            return
        _walk(node.left, prefix + '0')
        _walk(node.right, prefix + '1')

    _walk(root)
    return codes


def _compress_huffman(data: bytes) -> tuple[bytes, bytes]:
    freq_table = [0] * 256
    for b in data:
        freq_table[b] += 1

    codes = _build_huffman_codes(freq_table)
    bit_string = ''.join(codes[b] for b in data)
    bit_length = len(bit_string)
    pad_length = (-bit_length) % 8
    bit_string += '0' * pad_length

    compressed_bytes = bytes(int(bit_string[i:i+8], 2) for i in range(0, len(bit_string), 8))
    metadata = struct.pack('<Q', bit_length)
    metadata += b''.join(struct.pack('<Q', freq) for freq in freq_table)
    return compressed_bytes, metadata


def _compress_lzw(data: bytes) -> tuple[bytes, bytes]:
    dictionary = {bytes([i]): i for i in range(256)}
    dict_size = 256
    w = b''
    codes = []

    for byte in data:
        wc = w + bytes([byte])
        if wc in dictionary:
            w = wc
        else:
            codes.append(dictionary[w])
            if dict_size < 65536:
                dictionary[wc] = dict_size
                dict_size += 1
            else:
                dictionary = {bytes([i]): i for i in range(256)}
                dict_size = 256
            w = bytes([byte])

    if w:
        codes.append(dictionary[w])

    compressed_bytes = b''.join(struct.pack('<H', code) for code in codes)
    return compressed_bytes, b''


def _write_archive(output_path: str, entries: list[tuple[str, bytes, bytes, int]], algorithm_id: int):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'wb') as f:
        f.write(ARCHIVE_MAGIC)
        f.write(struct.pack('<B', ARCHIVE_VERSION))
        f.write(struct.pack('<B', algorithm_id))
        f.write(struct.pack('<I', len(entries)))

        for rel_path, compressed_bytes, metadata, original_size in entries:
            nome_bytes = rel_path.replace('\\', '/').encode('utf-8')
            f.write(struct.pack('<H', len(nome_bytes)))
            f.write(nome_bytes)
            f.write(struct.pack('<Q', original_size))
            f.write(struct.pack('<I', len(metadata)))
            f.write(metadata)
            f.write(struct.pack('<Q', len(compressed_bytes)))
            f.write(compressed_bytes)


def create_backup_files(dados_dir='dados', output_dir='backups') -> tuple[str, str]:
    arquivos = _gather_data_files(dados_dir)
    if not arquivos:
        raise FileNotFoundError(f"Nenhum arquivo encontrado em '{dados_dir}'.")

    huffman_entries = []
    lzw_entries = []

    for caminho, rel_path in arquivos:
        with open(caminho, 'rb') as f:
            dados = f.read()
        original_size = len(dados)
        huff_bytes, huff_meta = _compress_huffman(dados)
        lzw_bytes, lzw_meta = _compress_lzw(dados)
        huffman_entries.append((rel_path, huff_bytes, huff_meta, original_size))
        lzw_entries.append((rel_path, lzw_bytes, lzw_meta, original_size))

    arquivo_huffman = os.path.join(output_dir, 'backup_huffman.bin')
    arquivo_lzw = os.path.join(output_dir, 'backup_lzw.bin')
    _write_archive(arquivo_huffman, huffman_entries, ALGO_HUFFMAN)
    _write_archive(arquivo_lzw, lzw_entries, ALGO_LZW)

    return arquivo_huffman, arquivo_lzw


if __name__ == '__main__':
    print('backup.py não é um módulo executável diretamente. Use create_backup_files().')
