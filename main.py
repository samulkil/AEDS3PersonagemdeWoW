import sys
import os

# Ajuste de caminho para garantir que os módulos sejam encontrados
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from model.Personagem import Personagem
from model.Conta import Conta
from dao.PersonagemDAO import PersonagemDAO
from dao.ContaDAO import ContaDAO
from dao.GrupoTempDAO import GrupoTempDAO

# Instâncias dos DAOs
dao_conta = ContaDAO()
dao_perso = PersonagemDAO()
dao_grupo_memoria = GrupoTempDAO()

def menu_grupos(id_conta_logada):
    while True:
        print("\n" + "-"*30)
        print("  GERENCIAR GRUPOS (VOLÁTIL)  ")
        print("-"*30)
        print("1. Criar um Grupo (e entrar)")
        print("2. Convidar Personagem a um grupo")
        print("3. Listar Membros de um Grupo")
        print("4. Voltar")
        
        op = input("\nEscolha uma opção: ")

        if op == "1":
            print("\nSelecione o personagem para criar o grupo:")
            dao_perso.listar_por_conta(id_conta_logada)
            try:
                id_p = int(input("Digite o ID do Personagem: "))
                p_check = dao_perso.read_by_id_and_conta(id_p, id_conta_logada)
                if p_check:
                    novo_id = dao_grupo_memoria.criar_grupo_automatico(id_conta_logada, id_p, dao_perso)
                else:
                    print("[Erro] Personagem inválido ou não pertence a você.")
            except ValueError:
                print("[Erro] Entrada inválida.")

        elif op == "2":
            try:
                id_g = int(input("ID do grupo para entrar: "))
                dao_perso.listar_por_conta(id_conta_logada)
                id_p = int(input("ID do seu Personagem: "))
                # CORREÇÃO: Passando dao_perso para validar a regra 1/1/3
                dao_grupo_memoria.adicionar_ao_grupo(id_g, id_conta_logada, id_p, dao_perso)
            except ValueError:
                print("[Erro] Entrada inválida.")

        elif op == "3":
            try:
                id_g = int(input("ID do grupo para listar: "))
                membros = dao_grupo_memoria.listar_membros_do_grupo(id_g)
                if membros:
                    print(f"\n--- Membros do Grupo {id_g} ({len(membros)}/5) ---")
                    for m in membros:
                        p = dao_perso.read(m.id_personagem)
                        f_str = p.funcao.decode().strip('\x00') if p else "???"
                        print(f"ID Personagem: {m.id_personagem} | Função: {f_str}")
                else:
                    print("\nGrupo não encontrado ou vazio.")
            except ValueError:
                print("[Erro] ID inválido.")
        
        elif op == "4":
            break

def menu_personagens(id_conta_logada, nome_usuario):
    while True:
        print(f"\n" + "="*45)
        print(f" LOGADO COMO: {nome_usuario} (ID: {id_conta_logada})")
        print("="*45)
        print("1. Criar Personagem")
        print("2. Pesquisar Personagem (Hash Extensível - ID)")
        print("3. Pesquisar Personagem (Árvore B+ - ID)")
        print("4. Pesquisar Personagem por Nível (B+)")
        print("5. Listar MEUS Personagens (Indexado 1:N)")
        print("6. Atualizar Personagem")
        print("7. Excluir Personagem (Lógica)")
        print("8. Gerenciar Grupos Temporários")
        print("9. Logout / Voltar")
        
        op = input("\nEscolha uma opção: ")

        if op == "1":
            nome = input("Nome do personagem: ")
            nivel = float(input("Nível inicial: "))
            
            while True:
                funcao = input("Função (dano, tanque, suporte): ").lower()
                if funcao in ["dano", "tanque", "suporte"]:
                    break
                print("[Erro] Escolha uma função válida!")

            novo_p = Personagem(0, nome, nivel, id_conta_logada, funcao)
            dao_perso.create(novo_p) # Sincroniza Hash e B+

        elif op == "2":
            try:
                id_busca = int(input("Digite o ID (Busca Hash): "))
                p = dao_perso.read(id_busca) # Busca direta O(1) via Hash
                if p and p.id_conta == id_conta_logada:
                    funcao_str = p.funcao.decode('utf-8').strip('\x00')
                    print(f"\n[Hash] ID: {p.id} | Nome: {p.nome.decode().strip()} | Função: {funcao_str}")
                else:
                    print("\n[Erro] Personagem não encontrado ou acesso negado.")
            except ValueError:
                print("\n[Erro] ID inválido.")

        elif op == "3":
            try:
                id_busca = int(input("Digite o ID (Busca B+): "))
                p = dao_perso.read_bplus(id_busca) # Busca via B+
                if p and p.id_conta == id_conta_logada:
                    print(f"\n[B+] ID: {p.id} | Nome: {p.nome.decode().strip()} | Nível: {p.nivel}")
                else:
                    print("\n[Erro] Registro não encontrado na árvore.")
            except ValueError:
                print("\n[Erro] Entrada inválida.")
                
        elif op == "4":
            try:
                nivel = float(input("Digite o nível para busca (B+): "))
                lista = dao_perso.buscar_por_nivel(nivel) # Busca indexada
                if lista:
                    print("\n--- Personagens encontrados ---")
                    for p in lista:
                        print(f"ID: {p.id} | Nome: {p.nome.decode().strip()} | Nível: {p.nivel}")
                else:
                    print("\nNenhum personagem com este nível.")
            except ValueError:
                print("\n[Erro] Entrada inválida.")

        elif op == "5":
            print(f"\n{'ID':<5} | {'Nome':<20} | {'Nível':<10} | {'Função':<10}")
            print("-" * 55)
            # Relacionamento 1:N via Hash Extensível
            dao_perso.listar_por_conta(id_conta_logada)

        elif op == "6":
            try:
                id_up = int(input("ID do personagem para atualizar: "))
                p_check = dao_perso.read(id_up)
                if p_check and p_check.id_conta == id_conta_logada:
                    n_nome = input(f"Novo Nome [{p_check.nome.decode().strip()}]: ") or p_check.nome.decode().strip()
                    n_nivel = input(f"Novo Nível [{p_check.nivel}]: ")
                    n_nivel = float(n_nivel) if n_nivel else p_check.nivel
                    
                    while True:
                        f_atual = p_check.funcao.decode().strip('\x00')
                        n_funcao = input(f"Nova Função [{f_atual}]: ").lower() or f_atual
                        if n_funcao in ["dano", "tanque", "suporte"]: break
                        print("[Erro] Função inválida.")

                    dao_perso.update(id_up, n_nome, n_nivel, id_conta_logada, n_funcao)
                    print("\n[Sucesso] Personagem atualizado!")
                else:
                    print("\n[Erro] Acesso negado.")
            except ValueError:
                print("\n[Erro] Entrada inválida.")

        elif op == "7":
            try:
                id_del = int(input("ID para excluir: "))
                p_check = dao_perso.read(id_del)
                if p_check and p_check.id_conta == id_conta_logada:
                    dao_perso.delete(id_del) # Exclusão lógica
                    print("\n[Sucesso] Personagem excluído logicamente.")
            except ValueError:
                print("\n[Erro] ID inválido.")

        elif op == "8":
            menu_grupos(id_conta_logada)

        elif op == "9":
            break

def menu_contas():
    while True:
        print("\n" + "#"*45)
        print("     SISTEMA DE RPG - AED III (PUC MINAS)     ")
        print("#"*45)
        print("1. Criar Nova Conta")
        print("2. Pesquisar Conta (Hash Extensível)")
        print("3. Atualizar Dados da Conta")
        print("4. Excluir Conta (Lógica + Hash)")
        print("5. ENTRAR (Login)")
        print("6. Ordenação Externa (por Usuário)")
        print("7. Sair do Programa")
        
        opcao = input("\nEscolha uma opção: ")

        if opcao == "1":
            u = input("Usuário: ")
            e = input("E-mail: ")
            d = input("Data (DD/MM/AAAA): ")
            dao_conta.create(Conta(0, u, e, d))

        elif opcao == "2":
            try:
                id_c = int(input("ID da Conta: "))
                c = dao_conta.read(id_c)
                if c: print(f"\n[Hash] Usuário: {c.usuario} | E-mail: {c.email}")
                else: print("\nConta não encontrada no índice.")
            except ValueError: print("\nID inválido.")

        elif opcao == "3":
            try:
                id_c = int(input("ID para atualizar: "))
                conta_existente = dao_conta.read(id_c)
                if conta_existente:
                    u = input(f"Novo Usuário [{conta_existente.usuario}]: ") or conta_existente.usuario
                    e = input(f"Novo Email [{conta_existente.email}]: ") or conta_existente.email
                    d = input(f"Nova Data [{conta_existente.data}]: ") or conta_existente.data
            
                    conta_atualizada = Conta(id_c, u, e, d)
                    dao_conta.update(id_c, conta_atualizada)
                    print("\n[Sucesso] Conta atualizada!")
                else:
                    print("\n[Erro] Conta não encontrada.")
            except ValueError: 
                print("\nErro na entrada.")

        elif opcao == "4":
            try:
                id_c = int(input("ID para deletar: "))
                if dao_conta.delete(id_c):
                    print("Exclusão concluída com sucesso.")
            except ValueError: print("\nID inválido.")

        elif opcao == "5":
            user_login = input("Digite seu USUÁRIO: ")
            conta = dao_conta.read_por_usuario(user_login)
            if conta:
                menu_personagens(conta.id, conta.usuario)
            else:
                print("\n[Erro] Login inválido ou conta excluída.")

        elif opcao == "6":
            print("\nIniciando Ordenação Externa (Intercalação Balanceada)...")
            dao_conta.ordenar_externo_usuario() # Ordenação por runs
            print("Arquivo 'contas_ordenadas.bin' gerado.")

        elif opcao == "7":
            print("Encerrando sistema...")
            break

if __name__ == "__main__":
    menu_contas()