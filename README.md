# Sistema de comandas — Restaurante

Aplicação web didática em **Python (Flask)**, **SQLite** e **HTML/CSS/JavaScript** (sem framework de front-end), para gestão de **comandas**, **caixa**, **administração** (cardápio, usuários, insumos, compras, receitas) e **resumo financeiro**, com controle de acesso por **papel** (admin, caixa, garçom).

## Documentação por entrega

| Arquivo | Conteúdo |
|---------|----------|
| [README_ENTREGA_1.md](README_ENTREGA_1.md) | Primeira entrega: núcleo pedagógico (camadas, SQLite, API, front com cardápio e fluxo inicial). |
| [README_ENTREGA_2.md](README_ENTREGA_2.md) | Segunda entrega: comandas, papéis, sidebar, modal de lançamento, estoque, notas de compra, ficha técnica, financeiro. |

## Stack

| Camada   | Tecnologia |
|----------|------------|
| Banco    | SQLite (`dados.db`) |
| Backend  | Python 3 + Flask |
| Front    | HTML, CSS, JS (fetch), templates Jinja2 |

## Pré-requisitos

- Python 3 instalado.

## Como rodar

Pasta do projeto (ajuste o caminho se a sua cópia estiver em outro lugar):

`/Users/matheus/Documents/github/restauranteapp`

### Ambiente virtual (recomendado)

**macOS / Linux (zsh/bash):**

```bash
cd /Users/matheus/Documents/github/restauranteapp
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 init_db.py
python3 app.py
```

**Windows (cmd):**

```cmd
cd C:\caminho\para\restauranteapp
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
python init_db.py
python app.py
```

Com o venv ativo, o prompt costuma começar com `(.venv)`.

### Sem venv

```bash
cd /Users/matheus/Documents/github/restauranteapp
pip3 install -r requirements.txt
python3 init_db.py
python3 app.py
```

O **`init_db.py`** também dispara o **`seed_demo_estoque.py`**: se ainda não houver insumos, são criados **insumos de exemplo**, **cinco notas de compra** e **receitas (ficha técnica)** para os itens do cardápio. Para pular isso, apague ou comente a chamada no final de `init_db.py`. Para **reaplicar** o seed num banco já usado, é preciso esvaziar/remover insumos (ou apagar `dados.db` e rodar `init_db.py` de novo).

1. **`init_db.py`** — cria `dados.db` e tabelas iniciais (rode na primeira vez ou após apagar o banco).
2. **`app.py`** — ao importar o módulo, executa **`ensure_schema()`** (cria/ajusta tabelas). Se a tabela **`usuarios`** estiver **vazia**, é criado automaticamente um usuário **`admin`** com senha **`admin123`** (troque em produção).
3. Acesse **`/login`**. Demais usuários podem ser cadastrados na tela **Usuários** (como admin).

## Fluxo resumido

- **`/`** — redireciona para login ou para a home do papel (admin → visão geral, caixa → caixa, garçom → salão).
- **Garçom** — apenas **Salão**: abrir/editar comandas e lançar itens no **modal** (estilo PDV).
- **Caixa** — **Caixa** (comandas, pagamento, lançar/editar itens) e **Financeiro (caixa)**.
- **Admin** — todas as telas de administração, salão, caixa e ambos os financeiros.

A **barra lateral** é **fixa** (permanece na tela ao rolar o conteúdo) e **a mesma estrutura** em todas as páginas autenticadas; só entram os **links permitidos ao papel** atual.

## Estrutura do projeto (principal)

```
├── README.md                 ← Visão geral (este arquivo)
├── README_ENTREGA_1.md
├── README_ENTREGA_2.md
├── ROTEIRO.md
├── requirements.txt
├── app.py                    ← Rotas, API e regras de negócio
├── init_db.py                ← Criação do SQLite (+ seed de estoque se vazio)
├── seed_demo_estoque.py      ← Insumos, notas e receitas de demonstração
├── dados.db                  ← Gerado após init_db
├── static/
│   ├── style.css
│   ├── app.js
│   ├── comandas_modal.js
│   └── admin_*.js            ← Telas admin específicas
└── templates/
    ├── login.html
    ├── layout_admin.html
    ├── layout_operacional.html
    ├── _sidebar_staff.html   ← Menu lateral único (por papel)
    ├── garcom.html
    ├── caixa.html
    ├── caixa_financeiro.html
    └── admin/                ← Páginas fragmentadas da administração
```

## API (visão geral)

As rotas **`/api/*`** exigem sessão autenticada; várias exigem papel **admin** ou combinações (comandas: admin/caixa/garçom; pagamento: admin/caixa; cardápio escrita: admin; etc.). Detalhes e lista completa em **README_ENTREGA_2.md**. Endpoints adicionais úteis: **`GET /api/admin/dashboard`** (métricas para a visão geral admin), **`GET /api/financeiro/ranking-itens`** (itens mais vendidos no período; admin e caixa).

Para roteiro de apresentação em sala, use **ROTEIRO.md** (ajuste se o roteiro ainda citar telas antigas).
