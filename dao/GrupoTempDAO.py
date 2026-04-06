class GrupoTempDAO:
    def __init__(self):
        # Armazena os IDs dos grupos já inicializados nesta sessão
        self.grupos_criados = [] 
        # Armazena os objetos GrupoTemp (membros)
        self.membros = []

    def criar_grupo_automatico(self, id_conta, id_personagem):
        """Cria um novo grupo com ID sequencial e já insere o criador"""
        # O novo ID é o próximo da sequência nesta sessão
        novo_id_grupo = len(self.grupos_criados) + 1
        self.grupos_criados.append(novo_id_grupo)
        
        # Como o grupo é novo, não precisamos validar limite ou conta repetida aqui
        from model.GrupoTemp import GrupoTemp
        primeiro_membro = GrupoTemp(novo_id_grupo, id_conta, id_personagem)
        self.membros.append(primeiro_membro)
        
        print(f"\n[SUCESSO] Grupo {novo_id_grupo} criado!")
        print(f"Personagem {id_personagem} adicionado como líder do grupo.")
        return novo_id_grupo

    def adicionar_ao_grupo(self, id_grupo, id_conta, id_personagem):
        """Adiciona membros a grupos JÁ EXISTENTES (via convite)"""
        if id_grupo not in self.grupos_criados:
            print(f"[ERRO] O Grupo {id_grupo} não existe nesta sessão.")
            return False

        # Filtra membros do grupo alvo
        membros_atuais = [m for m in self.membros if m.id_grupo == id_grupo]

        if len(membros_atuais) >= 5:
            print(f"[ERRO] Grupo {id_grupo} lotado (5/5).")
            return False

        for m in membros_atuais:
            if m.id_conta == id_conta:
                print(f"[ERRO] Você já tem um personagem neste grupo!")
                return False

        from model.GrupoTemp import GrupoTemp
        self.membros.append(GrupoTemp(id_grupo, id_conta, id_personagem))
        print(f"[SUCESSO] Personagem {id_personagem} entrou no Grupo {id_grupo}.")
        return True

    def listar_membros_do_grupo(self, id_grupo_alvo):
        return [m for m in self.membros if m.id_grupo == id_grupo_alvo]