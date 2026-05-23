from cs50 import SQL

# Conectar ao banco de dados (ou criar um se não existir)
db = SQL("sqlite:///loja.db")

# Criar a tabela produtos
db.execute('''
CREATE TABLE IF NOT EXISTS produtos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    descricao TEXT,
    cores TEXT,  -- String com cores separadas por vírgulas
    precos TEXT, -- String com preços separados por vírgulas
    imagens TEXT -- String com nomes ou URLs das imagens separadas por vírgulas
)
''')

# Função para adicionar um produto
def adicionar_produto(nome, descricao, cores, precos, imagens):
    db.execute("""
        INSERT INTO produtos (nome, descricao, cores, precos, imagens)
        VALUES (?, ?, ?, ?, ?)
    """, nome, descricao, ', '.join(cores), ', '.join(map(str, precos)), ', '.join(imagens))

# Função para perguntar quantas cores o usuário quer adicionar
def adicionar_cores():
    num_cores = int(input("Quantas cores deseja adicionar? "))
    cores = [input(f"Cor {i+1}: ") for i in range(num_cores)]
    return cores

# Função para perguntar os preços conforme o número de cores
def adicionar_precos(num_precos):
    precos = [float(input(f"Preço {i+1}: ")) for i in range(num_precos)]
    return precos

# Função para perguntar quantas imagens o usuário quer adicionar
def adicionar_imagens():
    num_imagens = int(input("Quantas imagens deseja adicionar? "))
    imagens = [input(f"Imagem {i+1} (nome ou URL): ") for i in range(num_imagens)]
    return imagens

# Função para adicionar um produto com número variável de cores, preços e imagens
def adicionar_produto_dinamico():
    nome = input("Nome do produto: ")
    descricao = input("Descrição do produto: ")

    cores = adicionar_cores()
    precos = adicionar_precos(len(cores))
    imagens = adicionar_imagens()

    adicionar_produto(nome, descricao, cores, precos, imagens)

# Inserir 100 produtos com inputs
def adicionar_100_produtos():
    for i in range(2):
        print(f"\nAdicionando produto {i+1}:")
        adicionar_produto_dinamico()

# Chamar a função para inserir 100 produtos
adicionar_100_produtos()
