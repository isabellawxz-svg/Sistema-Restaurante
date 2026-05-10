# Entrega 2 — Operação de restaurante (comandas, papéis, estoque e financeiro)

Esta entrega descreve **tudo que foi aplicado** na segunda fase: modelo mais próximo de um **PDV / comandas**, **separação de telas**, **permissões por usuário**, **insumos e estoque**, **compras manuais**, **ficha técnica** (receita do prato) e **acompanhamento financeiro**.

## 1. Autenticação e papéis

- **Login** com sessão Flask; senha armazenada com **hash** (no ambiente do projeto, `pbkdf2:sha256` quando `scrypt` não está disponível).
- Na **primeira subida** com banco sem usuários, `ensure_schema()` em `app.py` cria **`admin` / `admin123`** (apenas enquanto a tabela `usuarios` estiver vazia).
- Papéis: **`admin`**, **`caixa`**, **`garcom`**.
- **`/`** redireciona conforme o papel (admin → visão geral, caixa → caixa, garçom → salão).
- **Admin**: acesso total às rotas de administração e à operação (salão, caixa, financeiros).
- **Caixa**: comandas no caixa (incluindo lançar/editar itens), **pagamento** de comandas, **Financeiro (caixa)**.
- **Garçom**: apenas **Salão** — comandas, lançar/editar itens; **sem** telas de administração nem financeiro.

## 2. Interface: sidebar fixa e menu por papel

- **`templates/_sidebar_staff.html`**: menu **único** incluído em **`layout_admin.html`** e **`layout_operacional.html`**, para a barra **não “trocar de desenho”** ao mudar de admin para salão/caixa.
- **CSS** (`static/style.css`): sidebar com **`position: fixed`**, altura da viewport, rolagem interna se precisar; área principal com **`margin-left: 220px`**.
- Links **condicionais ao `session.role`**: garçom vê só **Salão**; caixa vê **Caixa** e **Financeiro (caixa)**; admin vê bloco **Administração** completo mais **Operação** (salão, caixa, financeiro caixa).
- Rodapé da sidebar: **nome** e **Sair** (unificado com a operação).

## 3. Comandas e modal de itens

- Substituição do fluxo antigo de “pedidos soltos” por **comandas** (mesa/cliente, status aberta/fechada, pagamento).
- **Salão** e **Caixa**: lançamento de itens do cardápio ao **abrir a comanda em modal** (`static/comandas_modal.js`), no estilo de sistemas tradicionais de comanda/PDV.
- APIs REST em **`/api/comandas`** (listar, criar, obter uma, atualizar, excluir) e **`PATCH .../pagamento`** para registrar forma de pagamento e fechar.

## 4. Estoque, insumos, notas de compra e ficha técnica

- **Insumos** com **estoque atual** e unidade; CRUD em **`/api/insumos`** (admin).
- **Notas de compra** lançadas **manualmente** (cabeçalho + linhas: insumo, quantidade, valor unitário); ao gravar a nota, o sistema **entra estoque** dos insumos (`/api/notas-compra`).
- **Composição / receita** por item do cardápio: insumo + quantidade consumida **por unidade vendida** do prato (`GET/PUT /api/cardapio/<id>/composicao`).
- Na **quitação da comanda**, o backend calcula o consumo de insumos a partir das quantidades vendidas e da composição, **valida estoque** e **baixa** antes de concluir o pagamento (transação SQLite); se faltar estoque, o pagamento é **bloqueado** com mensagem de erro.

## 5. Financeiro

- **`/admin/financeiro`**: página de resumo para admin.  
- **`/caixa/financeiro`**: mesma ideia de resumo para caixa (e admin pode abrir pelos dois atalhos).  
- **`GET /api/financeiro/resumo?inicio=YYYY-MM-DD&fim=YYYY-MM-DD`** (admin e caixa): receita de comandas **pagas** no período (usa `total_quitacao` quando existir), totais por **forma de pagamento**, e valor agregado das **linhas de nota de compra** no período (compras registradas).

## 6. Administração fragmentada em telas

- Rotas dedicadas: **`/admin/visao`**, **`/admin/cardapio`**, **`/admin/usuarios`**, **`/admin/insumos`**, **`/admin/notas-compra`**, **`/admin/receitas`**, **`/admin/financeiro`**.
- Templates em **`templates/admin/*.html`** estendendo **`layout_admin.html`**.
- Scripts auxiliares em **`static/`** (`admin_financeiro.js`, `admin_insumos.js`, `admin_notas.js`, `admin_receitas.js`, etc.).

## 7. Banco e script inicial

- **`init_db.py`**: cria tabelas alinhadas ao esquema atual (cardápio, comandas, itens de comanda, insumos, notas, itens de nota, composição, usuários) e insere **itens de exemplo** no cardápio se estiver vazio.
- **`seed_demo_estoque.py`**: chamado ao final do `init_db.py` quando **não existe nenhum insumo** — cadastra **vários insumos**, **cinco notas de compra** (com linhas e entrada em estoque, como na API) e **composição/receita** para Hambúrguer, Misto Quente, Pão na Chapa, Café, Suco de Laranja e Batata Frita. Pode ser executado sozinho: `python3 seed_demo_estoque.py`.
- Migrações incrementais podem ainda ser aplicadas em **`app.py`** na subida (`ensure_schema` ou equivalente), conforme evolução do projeto.

## 8. Arquivos principais tocados nesta entrega

| Área | Arquivos (exemplos) |
|------|---------------------|
| Regras e API | `app.py` |
| Modal comandas | `static/comandas_modal.js`, `static/app.js` |
| Layout / menu | `templates/layout_admin.html`, `templates/layout_operacional.html`, `templates/_sidebar_staff.html` |
| Estilo shell + modal | `static/style.css` |
| Telas | `templates/garcom.html`, `templates/caixa.html`, `templates/caixa_financeiro.html`, `templates/admin/*` |

## 9. Resumo da API (entrega 2)

| Método | Rota | Quem (resumo) |
|--------|------|----------------|
| GET/POST | `/api/cardapio` | GET: staff; POST: admin |
| PUT/DELETE | `/api/cardapio/<id>` | admin |
| GET/POST | `/api/usuarios` | admin |
| PUT | `/api/usuarios/<id>` | admin |
| GET/POST/PUT/DELETE | `/api/comandas`, `/api/comandas/<id>` | admin, caixa, garçom (conforme operação) |
| PATCH | `/api/comandas/<id>/pagamento` | admin, caixa |
| GET/POST/PUT/DELETE | `/api/insumos` | admin (escrita) |
| GET/POST | `/api/notas-compra` | admin |
| GET/PUT | `/api/cardapio/<id>/composicao` | admin |
| GET | `/api/financeiro/resumo` | admin, caixa |
| GET | `/api/financeiro/ranking-itens` | admin, caixa — query: `inicio`, `fim`, `limit` |
| GET | `/api/admin/dashboard` | admin — comandas abertas, receita do dia, alertas de estoque |

*(Detalhes de corpo JSON e códigos de erro: ver implementação em `app.py`.)*

## 10. Como demonstrar na banca (sugestão)

1. Login como **admin** → cadastrar insumos → lançar **nota de compra** → conferir estoque.  
2. Definir **composição** de um item do cardápio.  
3. Login **garçom** → abrir comanda no **modal** → lançar itens.  
4. Login **caixa** → **pagar** comanda e ver **baixa** de estoque; tentar pagar com estoque insuficiente para mostrar o bloqueio.  
5. Abrir **Financeiro** com intervalo de datas que inclua a comanda paga e a nota de compra.
