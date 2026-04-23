class GrupoTempDAO:
    def __init__(self):
        # Armazena os IDs dos grupos já inicializados nesta sessão
        self.grupos_criados = [] 
        # Armazena os objetos GrupoTemp (membros)
        self.membros = []

<<<<<<< Updated upstream
    def criar_grupo_automatico(self, id_conta, id_personagem):
        """Cria um novo grupo com ID sequencial e já insere o criador"""
        # O novo ID é o próximo da sequência nesta sessão
=======
    def _contar_funcoes(self, id_grupo, dao_perso):
        """
        Conta quantas funções de cada tipo existem no grupo atual.
        Utiliza o dao_perso para ler os dados do arquivo binário.
        """
        contagem = {"tanque": 0, "suporte": 0, "dano": 0}
        membros_grupo = [m for m in self.membros if m.id_grupo == id_grupo]
        
        for m in membros_grupo:
            p = dao_perso.read(m.id_personagem) # Busca direta via Hash no arquivo
            if p:
                # Decodifica e limpa a string da função vinda do binário
                funcao = p.funcao.decode('utf-8').strip('\x00').lower()
                if funcao in contagem:
                    contagem[funcao] += 1
        return contagem

    def criar_grupo_automatico(self, id_conta, id_personagem, dao_perso):
        """
        Cria um novo grupo e insere o líder.
        Assinatura ajustada para aceitar dao_perso conforme o server.py.
        """
        # Valida se o personagem existe antes de criar o grupo
        p_lider = dao_perso.read_by_id_and_conta(id_personagem, id_conta)
        if not p_lider:
            print("[ERRO] Personagem líder não encontrado ou não pertence a sua conta.")
            return None

>>>>>>> Stashed changes
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

<<<<<<< Updated upstream
        # Filtra membros do grupo alvo
        membros_atuais = [m for m in self.membros if m.id_grupo == id_grupo]

        if len(membros_atuais) >= 5:
            print(f"[ERRO] Grupo {id_grupo} lotado (5/5).")
            return False

        for m in membros_atuais:
            if m.id_conta == id_conta:
                print(f"[ERRO] Você já tem um personagem neste grupo!")
                return False
=======
        # 1. Busca os dados do personagem que deseja entrar
        p_novo = dao_perso.read_by_id_and_conta(id_personagem, id_conta)
        if not p_novo:
            print("[ERRO] Personagem não encontrado ou não pertence a sua conta.")
            return False
        
        funcao_nova = p_novo.funcao.decode('utf-8').strip('\x00').lower()

        # 2. Verifica se a conta já possui um personagem no grupo

        # 3. Verifica se a conta já possui um personagem no grupo
        if any(m.id_conta == id_conta and m.id_grupo == id_grupo for m in self.membros):
            print("[ERRO] Você já tem um herói neste grupo!")
            return False

        # 4. Validação da Regra de Composição (1/1/3)
        contagem = self._contar_funcoes(id_grupo, dao_perso)
        
        if funcao_nova == "tanque" and contagem["tanque"] >= 1:
            print("[ERRO] O grupo já possui o limite de 1 Tanque.")
            return False
        elif funcao_nova == "suporte" and contagem["suporte"] >= 1:
            print("[ERRO] O grupo já possui o limite de 1 Suporte.")
            return False
        elif funcao_nova == "dano" and contagem["dano"] >= 3:
            print("[ERRO] O grupo já possui o limite de 3 personagens de Dano.")
            return False
>>>>>>> Stashed changes

        from model.GrupoTemp import GrupoTemp
        self.membros.append(GrupoTemp(id_grupo, id_conta, id_personagem))
        print(f"[SUCESSO] Personagem {id_personagem} entrou no Grupo {id_grupo}.")
        return True

    def listar_membros_do_grupo(self, id_grupo_alvo):
        return [m for m in self.membros if m.id_grupo == id_grupo_alvo]