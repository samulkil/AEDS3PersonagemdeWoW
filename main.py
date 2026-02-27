import struct
from Personagem import Personagem, ArquivoPerso
from Conta import Conta, ArquivoConta

def menu_personagens(id_conta_logada, nome_usuario):
    db_perso = ArquivoPerso()
    
    while True:
        print(f"\n" + "="*40)
        print(f" LOGADO COMO: {nome_usuario} (ID: {id_conta_logada})")
        print("="*40)
        print("1. Criar Personagem")
        print("2. Pesquisar Personagem (por ID)")
        print("3. Listar MEUS Personagens")
        print("4. Atualizar Personagem")
        print("5. Excluir Personagem (Lógica)")
        print("6. Logout / Voltar")
        
        op = input("\nEscolha uma opção: ")

        if op == "1":
            nome = input("Nome do personagem: ")
            nivel = float(input("Nível inicial: "))
            novo_p = Personagem(0, nome, nivel, id_conta_logada)
            db_perso.create(novo_p)

        elif op == "2":
            try:
                id_busca = int(input("Digite o ID do personagem: "))
                p = db_perso.read(id_busca)
                if p and p.id_conta == id_conta_logada:
                    nome_str = p.nome.decode('utf-8').strip('\x00')
                    print(f"\n[Sucesso] ID: {p.id} | Nome: {nome_str} | Nível: {p.nivel}")
                else:
                    print("\n[Erro] Personagem não encontrado ou acesso negado.")
            except ValueError:
                print("\n[Erro] Digite um ID numérico válido.")

        elif op == "3":
            # Não esquece isso aq é a lista 
            db_perso.listar_por_conta(id_conta_logada)

        elif op == "4":
            try:
                id_up = int(input("ID do personagem para atualizar: "))
                p_check = db_perso.read(id_up)
                if p_check and p_check.id_conta == id_conta_logada:
                    novo_nome = input("Novo Nome: ")
                    novo_nivel = float(input("Novo Nível: "))
                    db_perso.update(id_up, novo_nome, novo_nivel, id_conta_logada)
                else:
                    print("\n[Erro] Personagem não encontrado nesta conta.")
            except ValueError:
                print("\n[Erro] Entrada inválida.")

        elif op == "5":
            try:
                id_del = int(input("ID do personagem para excluir: "))
                p_check = db_perso.read(id_del)
                if p_check and p_check.id_conta == id_conta_logada:
                    db_perso.delete(id_del)
                else:
                    print("\n[Erro] Acesso negado.")
            except ValueError:
                print("\n[Erro] ID inválido.")

        elif op == "6":
            print(f"Efetuando logout de {nome_usuario}...")
            break

def menu_contas():
    db_conta = ArquivoConta()
    
    while True:
        print("\n" + "#"*40)
        print("     SISTEMA DE RPG - AED III (PUC MINAS)     ")
        print("#"*40)
        print("1. Criar Nova Conta")
        print("2. Pesquisar Conta (por ID)")
        print("3. Atualizar Dados da Conta")
        print("4. Excluir Conta (Lógica)")
        print("5. ENTRAR (Acessar Personagens)")
        print("6. Sair do Programa")
        
        opcao = input("\nEscolha uma opção: ")

        if opcao == "1":
            u = input("Nome de Usuário: ")
            e = input("E-mail: ")
            d = input("Data de Criação (DD/MM/AAAA): ")
            nova_c = Conta(0, u, e, d)
            db_conta.create(nova_c)

        elif opcao == "2":
            try:
                id_c = int(input("Digite o ID da Conta: "))
                c = db_conta.read(id_c)
                if c:
                    print(f"\n[Conta] Usuário: {c.usuario} | Email: {c.email} | Data: {c.data}")
                else:
                    print("\n[Erro] Conta inexistente.")
            except ValueError:
                print("\n[Erro] ID inválido.")

        elif opcao == "3":
            try:
                id_c = int(input("ID da conta para atualizar: "))
                u = input("Novo Usuário: ")
                e = input("Novo Email: ")
                d = input("Nova Data: ")
                db_conta.update(id_c, u, e, d)
            except ValueError:
                print("\n[Erro] Entrada inválida.")

        elif opcao == "4":
            try:
                id_c = int(input("ID da conta para deletar: "))
                if db_conta.delete(id_c):
                    print("\n[Sucesso] Conta desativada.")
                else:
                    print("\n[Erro] Não foi possível deletar.")
            except ValueError:
                print("\n[Erro] ID inválido.")

        elif opcao == "5":
            user_login = input("Digite o NOME DE USUÁRIO para logar: ")
            # Busca a conta pela string do usuário 
            conta = db_conta.read_por_usuario(user_login)
            
            if conta:
                #aqui ele já grava o ID/usuario da conta q ele pergou na linha 127 e p
                # passa como parametro!!! 
                menu_personagens(conta.id, conta.usuario)
            else:
                print("\n[Erro] Usuário não encontrado ou desativado!")

        elif opcao == "6":
            print("Encerrando sistema...")
            break
        else:
            print("\n[!] Opção inválida, tente novamente.")

if __name__ == "__main__":
    menu_contas()