# init_db.py
# Cria o SQLite: cardápio, comandas, insumos, notas/composição (estoque) e usuários na primeira subida do app.
# Rode: python init_db.py

import sqlite3

DB_PATH = "dados.db"


def criar_banco():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS itens_cardapio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            preco REAL NOT NULL,
            categoria TEXT NOT NULL DEFAULT ''
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS comandas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            mesa TEXT NOT NULL DEFAULT '',
            cliente_nome TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'aberta',
            pagamento_status TEXT NOT NULL DEFAULT 'pendente',
            forma_pagamento TEXT,
            fechada_em TIMESTAMP,
            total_quitacao REAL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS itens_comanda (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_comanda INTEGER NOT NULL,
            id_item INTEGER NOT NULL,
            quantidade INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (id_comanda) REFERENCES comandas(id),
            FOREIGN KEY (id_item) REFERENCES itens_cardapio(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS insumos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            unidade TEXT NOT NULL DEFAULT 'un',
            estoque_atual REAL NOT NULL DEFAULT 0,
            estoque_minimo REAL NOT NULL DEFAULT 0,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notas_compra (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fornecedor TEXT NOT NULL DEFAULT '',
            numero_nota TEXT NOT NULL DEFAULT '',
            data_nota TEXT NOT NULL DEFAULT '',
            observacao TEXT NOT NULL DEFAULT '',
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS itens_nota_compra (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_nota INTEGER NOT NULL,
            id_insumo INTEGER NOT NULL,
            quantidade REAL NOT NULL,
            valor_unitario REAL NOT NULL DEFAULT 0,
            FOREIGN KEY (id_nota) REFERENCES notas_compra(id),
            FOREIGN KEY (id_insumo) REFERENCES insumos(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS composicao_item (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_item_cardapio INTEGER NOT NULL,
            id_insumo INTEGER NOT NULL,
            quantidade REAL NOT NULL,
            UNIQUE (id_item_cardapio, id_insumo),
            FOREIGN KEY (id_item_cardapio) REFERENCES itens_cardapio(id),
            FOREIGN KEY (id_insumo) REFERENCES insumos(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            login TEXT NOT NULL UNIQUE,
            senha_hash TEXT NOT NULL,
            papel TEXT NOT NULL,
            nome_exibicao TEXT NOT NULL DEFAULT '',
            ativo INTEGER NOT NULL DEFAULT 1,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mesas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT NOT NULL UNIQUE,
            capacidade INTEGER NOT NULL DEFAULT 4,
            status TEXT NOT NULL DEFAULT 'livre',
            id_comanda_ativa INTEGER,
            FOREIGN KEY (id_comanda_ativa) REFERENCES comandas(id)
        )
    """)

    cursor.execute("PRAGMA table_info(comandas)")
    cols_comanda = {row[1] for row in cursor.fetchall()}
    if "id_mesa" not in cols_comanda:
        cursor.execute("ALTER TABLE comandas ADD COLUMN id_mesa INTEGER REFERENCES mesas(id)")

    cursor.execute("SELECT COUNT(*) FROM mesas")
    if cursor.fetchone()[0] == 0:
        for i in range(1, 13):
            cap = 4 if i <= 8 else 6
            cursor.execute(
                "INSERT INTO mesas (numero, capacidade, status) VALUES (?, ?, 'livre')",
                (str(i), cap),
            )

    cursor.execute("SELECT COUNT(*) FROM itens_cardapio")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO itens_cardapio (nome, preco, categoria) VALUES (?, ?, ?)",
            [
                ("Café", 5.00, "Bebidas"),
                ("Suco de Laranja", 8.00, "Bebidas"),
                ("Pão na Chapa", 4.50, "Lanches"),
                ("Misto Quente", 12.00, "Lanches"),
                ("Hambúrguer", 18.00, "Lanches"),
                ("Batata Frita", 10.00, "Acompanhamentos"),
            ],
        )

    conn.commit()
    conn.close()
    print("Banco criado com sucesso em", DB_PATH)

    try:
        from seed_demo_estoque import aplicar as seed_estoque_demo

        seed_estoque_demo()
    except Exception as exc:
        print("Aviso: não foi possível rodar o seed de estoque:", exc)


if __name__ == "__main__":
    criar_banco()
