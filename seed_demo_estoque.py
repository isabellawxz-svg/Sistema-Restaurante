# seed_demo_estoque.py
# Insere insumos de exemplo, notas de compra (entrada em estoque) e receitas (composição do cardápio).
# Só roda se a tabela insumos estiver vazia (evita duplicar em toda execução).
# Uso: python3 seed_demo_estoque.py   ou   chamado ao final de init_db.py

import sqlite3

DB_PATH = "dados.db"


def _mapa_insumos(cursor):
    cursor.execute("SELECT id, nome FROM insumos")
    return {row["nome"]: row["id"] for row in cursor.fetchall()}


def _mapa_cardapio(cursor):
    cursor.execute("SELECT id, nome FROM itens_cardapio")
    return {row["nome"]: row["id"] for row in cursor.fetchall()}


def aplicar():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) AS n FROM insumos")
    if cur.fetchone()["n"] > 0:
        conn.close()
        print("Seed de estoque ignorado: já existem insumos em", DB_PATH)
        return False

    insumos = [
        ("Pão de hambúrguer", "un"),
        ("Carne moída", "kg"),
        ("Queijo mussarela (fatia)", "un"),
        ("Tomate", "kg"),
        ("Alface", "un"),
        ("Café em pó", "kg"),
        ("Água filtrada", "L"),
        ("Laranja", "kg"),
        ("Pão de forma (fatia)", "un"),
        ("Manteiga", "kg"),
        ("Batata", "kg"),
        ("Óleo para fritura", "L"),
        ("Pão francês", "un"),
        ("Presunto (fatia)", "un"),
    ]
    for nome, un in insumos:
        cur.execute(
            "INSERT INTO insumos (nome, unidade, estoque_atual) VALUES (?, ?, 0)",
            (nome, un),
        )
    conn.commit()

    mid = _mapa_insumos(cur)

    def add_estoque(id_insumo, qtd):
        cur.execute(
            "UPDATE insumos SET estoque_atual = estoque_atual + ? WHERE id = ?",
            (qtd, id_insumo),
        )

    notas = [
        {
            "fornecedor": "Distribuidora Sul",
            "numero_nota": "NF-1001",
            "data_nota": "2026-04-01",
            "observacao": "Compra mensal secos",
            "linhas": [
                ("Café em pó", 2.0, 42.0),
                ("Óleo para fritura", 5.0, 11.5),
                ("Manteiga", 3.0, 36.0),
            ],
        },
        {
            "fornecedor": "Hortifruti Verde",
            "numero_nota": "555",
            "data_nota": "2026-04-05",
            "observacao": "",
            "linhas": [
                ("Tomate", 10.0, 5.8),
                ("Alface", 24.0, 2.2),
                ("Laranja", 18.0, 3.5),
            ],
        },
        {
            "fornecedor": "Padaria Central",
            "numero_nota": "PC-88",
            "data_nota": "2026-04-08",
            "observacao": "",
            "linhas": [
                ("Pão de hambúrguer", 48.0, 1.15),
                ("Pão de forma (fatia)", 120.0, 0.18),
                ("Pão francês", 80.0, 0.75),
            ],
        },
        {
            "fornecedor": "Açougue do Zé",
            "numero_nota": "AZ-202",
            "data_nota": "2026-04-09",
            "observacao": "",
            "linhas": [
                ("Carne moída", 10.0, 36.5),
                ("Presunto (fatia)", 40.0, 0.45),
                ("Queijo mussarela (fatia)", 50.0, 0.55),
            ],
        },
        {
            "fornecedor": "Atacado Batata",
            "numero_nota": "AT-7",
            "data_nota": "2026-04-10",
            "observacao": "",
            "linhas": [
                ("Batata", 25.0, 4.2),
                ("Água filtrada", 20.0, 0.35),
            ],
        },
    ]

    for n in notas:
        cur.execute(
            """
            INSERT INTO notas_compra (fornecedor, numero_nota, data_nota, observacao)
            VALUES (?, ?, ?, ?)
            """,
            (n["fornecedor"], n["numero_nota"], n["data_nota"], n["observacao"]),
        )
        id_nota = cur.lastrowid
        for nome_insumo, qtd, vu in n["linhas"]:
            iid = mid[nome_insumo]
            cur.execute(
                """
                INSERT INTO itens_nota_compra (id_nota, id_insumo, quantidade, valor_unitario)
                VALUES (?, ?, ?, ?)
                """,
                (id_nota, iid, qtd, vu),
            )
            add_estoque(iid, qtd)
    conn.commit()

    cid = _mapa_cardapio(cur)
    receitas = [
        ("Hambúrguer", [("Pão de hambúrguer", 1), ("Carne moída", 0.14), ("Queijo mussarela (fatia)", 2), ("Tomate", 0.025), ("Alface", 0.2)]),
        ("Misto Quente", [("Pão de forma (fatia)", 2), ("Presunto (fatia)", 2), ("Queijo mussarela (fatia)", 2), ("Manteiga", 0.012)]),
        ("Pão na Chapa", [("Pão francês", 1), ("Manteiga", 0.018)]),
        ("Café", [("Café em pó", 0.018)]),
        ("Suco de Laranja", [("Laranja", 0.28), ("Água filtrada", 0.15)]),
        ("Batata Frita", [("Batata", 0.22), ("Óleo para fritura", 0.04)]),
    ]

    for nome_prato, linhas in receitas:
        if nome_prato not in cid:
            continue
        id_item = cid[nome_prato]
        for nome_insumo, qtd in linhas:
            if nome_insumo not in mid:
                continue
            cur.execute(
                """
                INSERT OR REPLACE INTO composicao_item (id_item_cardapio, id_insumo, quantidade)
                VALUES (?, ?, ?)
                """,
                (id_item, mid[nome_insumo], qtd),
            )
    conn.commit()
    conn.close()
    print("Seed de estoque aplicado:", len(insumos), "insumos,", len(notas), "notas, receitas nos itens do cardápio.")
    return True


if __name__ == "__main__":
    aplicar()
