import struct
import os

class Conta:
    # Formato: 1s (Lápide), i (ID), 20s (Usuário), 30s (Email), 10s (Data)
    FORMATO = "1s i 20s 30s 10s" 

    def __init__(self, id, usuario, email, data, lapide=b' '):
        self.id = id
        # Tratamento de strings para bytes com tamanho fixo
        self.usuario = usuario.encode('utf-8')[:20] if isinstance(usuario, str) else usuario[:20]
        self.email = email.encode('utf-8')[:30] if isinstance(email, str) else email[:30]
        self.data = data.encode('utf-8')[:10] if isinstance(data, str) else data[:10]
        self.lapide = lapide

    def to_bytes(self):      
        usuario_f = self.usuario.ljust(20, b'\x00')
        email_f = self.email.ljust(30, b'\x00')
        data_f = self.data.ljust(10, b'\x00')
        return struct.pack(self.FORMATO, self.lapide, self.id, usuario_f, email_f, data_f)
    
    @classmethod 
    def from_bytes(cls, dados_binarios):
        lapide, id, usuario, email, data = struct.unpack(cls.FORMATO, dados_binarios)
        return cls(
            id, 
            usuario.decode('utf-8').strip('\x00'), 
            email.decode('utf-8').strip('\x00'), 
            data.decode('utf-8').strip('\x00'), 
            lapide
        )

class ArquivoConta:
    def __init__(self, nome_arquivo="contas.bin"):
        self.nome_arquivo = nome_arquivo
        self.formato_header = "i" 
        self.tamanho_header = struct.calcsize(self.formato_header)
        self.tamanho_registro = struct.calcsize(Conta.FORMATO)
        
        if not os.path.exists(self.nome_arquivo):
            with open(self.nome_arquivo, "wb") as f:
                f.write(struct.pack(self.formato_header, 0))
    
    def create(self, conta):
        with open(self.nome_arquivo, "rb+") as f:
            f.seek(0)
            ultimo_id = struct.unpack(self.formato_header, f.read(self.tamanho_header))[0]
            novo_id = ultimo_id + 1
            conta.id = novo_id
            
            f.seek(0, 2)
            f.write(conta.to_bytes())

            f.seek(0)
            f.write(struct.pack(self.formato_header, novo_id))
            print(f"Conta do usuário {novo_id} criada com sucesso!")

    def update(self, id_alvo, novo_usuario, novo_email, nova_data):
        """Atualiza os dados de uma conta existente (Fase 1)"""
        with open(self.nome_arquivo, "rb+") as f: # r+ permite leitura e escrita
            f.seek(self.tamanho_header) # Pula o ID de controle no início
            
            while True:
                posicao_atual = f.tell() # Salva o início do registro para o seek
                lapide = f.read(1)
                
                if not lapide:
                    print("Conta não encontrada.")
                    break

                # Lê o restante do registro (ID + Usuario + Email + Data)
                # O ponteiro avança durante a leitura para checar o ID
                dados_restantes = f.read(self.tamanho_registro - 1)
                id_lido = struct.unpack("i", dados_restantes[:4])[0]

                # Se for o ID buscado e a conta estiver ativa (lápide vazia)
                if id_lido == id_alvo and lapide == b' ':
                    f.seek(posicao_atual) # Volta para o byte exato onde o registro começa
                    
                    # Cria o objeto com os novos dados fornecidos
                    conta_atualizada = Conta(id_alvo, novo_usuario, novo_email, nova_data)
                    
                    # Sobrescreve os bytes antigos com os novos
                    f.write(conta_atualizada.to_bytes())
                    print(f"Conta {id_alvo} atualizada com sucesso!")
                    return True
        return False

    def read(self, id_alvo):
        with open(self.nome_arquivo, "rb") as f:
            f.seek(self.tamanho_header)
            while True:
                posicao_atual = f.tell()
                lapide = f.read(1)
                if not lapide:
                    break
                
                dados = f.read(self.tamanho_registro - 1)
                id_lido = struct.unpack("i", dados[:4])[0]

                if id_lido == id_alvo and lapide == b' ':
                    f.seek(posicao_atual)
                    return Conta.from_bytes(f.read(self.tamanho_registro))
        return None

    def delete(self, id_alvo):
        with open(self.nome_arquivo, "rb+") as f:
            f.seek(self.tamanho_header)
            while True:
                posicao_da_lapide = f.tell()
                lapide = f.read(1)
                if not lapide:
                    break
                
                dados = f.read(self.tamanho_registro - 1)
                id_lido = struct.unpack("i", dados[:4])[0]

                if lapide == b' ' and id_lido == id_alvo:
                    f.seek(posicao_da_lapide)
                    f.write(b'*') # Lápide de exclusão
                    return True
        return False