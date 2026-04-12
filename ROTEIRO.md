# Explicação do sistema – Pedidos de Restaurante

O sistema é dividido em três partes:  banco de dados, backend e frontend.

**Banco de dados:** os dados ficam no SQLite, no arquivo `dados.db`. O cardápio e os pedidos são gravados e lidos a partir daí.

**Backend:** o Flask (em `app.py`) sobe um servidor na porta 5000. Ele atende as URLs da aplicação: devolve as páginas HTML e, nas rotas da API, lê ou grava no banco e responde em JSON.

**Frontend:** duas telas em HTML/CSS/JavaScript. A página principal mostra o cardápio, o formulário para anotar pedido (itens e quantidades) e a lista de pedidos. A página de admin permite cadastrar, editar e excluir itens do cardápio. Em ambas há uma barra de navegação no topo para ir de uma tela à outra.

---

## Banco de dados

O banco é criado pelo script `init_db.py` (rodado uma vez). Há três tabelas:

- **itens_cardapio:** `id`, `nome`, `preco`. Cada linha é um item do cardápio.
- **pedidos:** `id`, `criado_em`. Cada linha é um pedido (só o cabeçalho).
- **itens_pedido:** `id_pedido`, `id_item`, `quantidade`. Liga cada pedido aos itens do cardápio e às quantidades.

O relacionamento é: um pedido tem vários itens (via `itens_pedido`), e cada item aponta para um registro em `itens_cardapio`. Ao anotar um pedido, inserimos uma linha em `pedidos` e várias em `itens_pedido`. Ao listar o cardápio ou os pedidos, fazemos SELECT nessas tabelas.

---

## Backend (API)

O servidor em `app.py` expõe:

- **Páginas:** `/` devolve a tela do cardápio e pedidos; `/admin` devolve a tela de cadastro de itens.

- **API (JSON):**
  - **GET /api/cardapio** — lista os itens do cardápio.
  - **POST /api/cardapio** — cadastra um item (nome e preço no body).
  - **PUT /api/cardapio/:id** — edita um item.
  - **DELETE /api/cardapio/:id** — exclui um item (e as linhas em `itens_pedido` que o referenciam).
  - **GET /api/pedidos** — lista todos os pedidos com seus itens.
  - **GET /api/pedidos/:id** — retorna um pedido com itens (para edição).
  - **POST /api/pedidos** — cria um pedido (body: lista de `id_item` e `quantidade`).
  - **PUT /api/pedidos/:id** — altera os itens do pedido (substitui as quantidades).
  - **DELETE /api/pedidos/:id** — exclui o pedido e seus itens.

O navegador chama essas URLs; o Flask acessa o SQLite e devolve os dados em JSON. É uma API REST simples.

---

## Frontend

Na página principal, o JavaScript carrega o cardápio com **GET /api/cardapio** e monta a lista e os campos de quantidade. Ao clicar em “Enviar pedido”, monta a lista de itens com quantidade maior que zero e envia **POST /api/pedidos**. A lista de pedidos vem de **GET /api/pedidos** (chamada ao carregar a página e depois de enviar ou alterar um pedido). Cada pedido exibe botões “Editar” e “Excluir”; editar abre um formulário de quantidades e salva com **PUT /api/pedidos/:id**; excluir chama **DELETE /api/pedidos/:id**.

Na página admin, o formulário de novo item envia **POST /api/cardapio**. A lista de itens é preenchida com **GET /api/cardapio**. Cada item tem “Editar” (campos inline de nome e preço, salvos com **PUT /api/cardapio/:id**) e “Excluir” (**DELETE /api/cardapio/:id**).

O HTML define a estrutura, o CSS o visual, e o JavaScript usa `fetch` para falar com a API e atualizar o que aparece na tela com a resposta.

---

## Fluxo de um pedido

O usuário escolhe itens e quantidades e clica em “Enviar pedido”. O JavaScript envia **POST /api/pedidos** com essa lista. O Flask insere uma linha em `pedidos` e as linhas correspondentes em `itens_pedido`. Depois o frontend chama **GET /api/pedidos** de novo e atualiza a lista na tela. O caminho é: tela → API → banco → API → tela.
