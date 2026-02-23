from Personagem import Personagem, ArquivoPerso

def menu():
    db = ArquivoPerso()
    
    while True:
        print("\n--- Gerenciamento de Personagens (Fase 1) ---")
        print("1. Criar Personagem")
        print("2. Pesquisar (Read)")
        print("3. Atualizar (Update)")
        print("4. Excluir (Delete)")
        print("5. Sair")
        
        opcao = input("Escolha uma opção: ")

        if opcao == "1":
            nome = input("Nome do personagem: ")
            nivel = float(input("Nível (ponto flutuante): "))
            # O ID é gerado automaticamente pelo seu método create
            novo_p = Personagem(0, nome, nivel)
            db.create(novo_p)

        elif opcao == "2":
            id_busca = int(input("ID para busca: "))
            p = db.read(id_busca)
            if p:
                print(f"\nEncontrado: ID: {p.id} | Nome: {p.nome.decode('utf-8').strip('\\x00')} | Nível: {p.nivel}")
            else:
                print("\nPersonagem não encontrado ou excluído.")

        elif opcao == "3":
            id_up = int(input("ID do personagem para atualizar: "))
            novo_nome = input("Novo Nome: ")
            novo_nivel = float(input("Novo Nível: "))
            db.update(id_up, novo_nome, novo_nivel)

        elif opcao == "4":
            id_del = int(input("ID para exclusão lógica: "))
            db.delete(id_del)

        elif opcao == "5":
            print("Saindo...")
            break
        else:
            print("Opção inválida!")

if __name__ == "__main__":
    menu()