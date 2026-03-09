# init_db.py
# Script executado UMA VEZ para criar as tabelas do banco SQLite.
# Cria: itens_cardapio (itens do cardápio), pedidos (cabeçalho do pedido),
# itens_pedido (itens de cada pedido). Rode antes de usar o sistema: python init_db.py

import sqlite3

DB_PATH = "dados.db"

def criar_banco():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Tabela de itens do cardápio: id, nome, preço
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS itens_cardapio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            preco REAL NOT NULL
        )
    """)

    # Tabela de pedidos: id do pedido e data/hora
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Tabela de itens do pedido: liga pedido -> item do cardápio e quantidade
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS itens_pedido (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_pedido INTEGER NOT NULL,
            id_item INTEGER NOT NULL,
            quantidade INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (id_pedido) REFERENCES pedidos(id),
            FOREIGN KEY (id_item) REFERENCES itens_cardapio(id)
        )
    """)

    # Inserir alguns itens de exemplo no cardápio
    cursor.execute("SELECT COUNT(*) FROM itens_cardapio")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO itens_cardapio (nome, preco) VALUES (?, ?)",
            [
                ("Café", 5.00),
                ("Suco de Laranja", 8.00),
                ("Pão na Chapa", 4.50),
                ("Misto Quente", 12.00),
                ("Hambúrguer", 18.00),
                ("Batata Frita", 10.00),
            ]
        )

    conn.commit()
    conn.close()
    print("Banco criado com sucesso em", DB_PATH)

if __name__ == "__main__":
    criar_banco()
