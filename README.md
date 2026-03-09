# Sistema de Pedidos de Restaurante

Projeto para demonstrar conceitos de **banco de dados**, **backend** e **frontend**: cardápio com itens pré-definidos (ou cadastrados), tela para anotar pedidos e tela simples para cadastrar itens no cardápio.

## Objetivo

Mostrar de forma didática como as três camadas funcionam juntas:

- **Banco de dados (SQLite):** armazena itens do cardápio e pedidos.
- **Backend (Flask):** API que lê e grava no banco e devolve dados em JSON.
- **Frontend (HTML/CSS/JS):** telas que consomem a API e exibem os dados.

## Stack

| Camada   | Tecnologia              |
|----------|-------------------------|
| Banco    | SQLite (arquivo `dados.db`) |
| Backend  | Python 3 + Flask        |
| Frontend | HTML, CSS e JavaScript (sem framework) |

## Pré-requisitos

- Python 3 instalado no PC.

## Como rodar

Abra o terminal (ou Prompt de Comando no Windows), entre na pasta do projeto e execute os comandos abaixo **um por vez**. O nome do comando de Python e do pip varia conforme o sistema.

### Linux e macOS

Geralmente o executável é `python3` e o gerenciador de pacotes é `pip3`:

```bash
pip3 install -r requirements.txt
python3 init_db.py
python3 app.py
```

### Windows

No Windows o comando costuma ser `python` e `pip`. Se não funcionar, tente `py` em vez de `python`:

```cmd
pip install -r requirements.txt
python init_db.py
python app.py
```

Ou, com `py`:

```cmd
py -m pip install -r requirements.txt
py init_db.py
py app.py
```

### Depois de subir o servidor

1. **Criar o banco** — `init_db.py` só precisa ser executado na primeira vez; ele cria o arquivo `dados.db` e insere itens de exemplo no cardápio.
2. Com `app.py` rodando, abra no navegador:
   - **Cardápio e pedidos:** http://127.0.0.1:5000  
   - **Cadastro de itens (admin):** http://127.0.0.1:5000/admin  

A navegação entre as telas é feita pela barra no topo. Na tela principal é possível **editar** e **excluir** pedidos; na tela admin é possível **editar** e **excluir** itens do cardápio.

## Estrutura do projeto

```
projeto-facu/
├── README.md          ← Este arquivo (explicação do projeto)
├── ROTEIRO.md         ← Roteiro para apresentar/explicar o sistema
├── requirements.txt   ← Dependências (Flask)
├── app.py             ← Servidor e rotas da API
├── init_db.py         ← Criação das tabelas no SQLite (rodar uma vez)
├── dados.db           ← Banco SQLite (gerado ao rodar init_db.py)
├── static/
│   ├── style.css      ← Estilos das páginas
│   └── app.js         ← Chamadas à API e atualização da tela
└── templates/
    ├── index.html     ← Página do cardápio e anotar pedido
    └── admin.html     ← Página para cadastrar itens no cardápio
```

## Conceitos demonstrados

- **Banco:** tabelas (`itens_cardapio`, `pedidos`, `itens_pedido`), INSERT, SELECT, relacionamento entre pedido e itens.
- **Backend:** rotas GET/POST, leitura e escrita no SQLite, respostas em JSON.
- **Frontend:** formulários, `fetch` para a API, exibição dinâmica dos dados (cardápio, pedidos, lista de itens no admin).

## API (resumo)

| Método | Rota                  | Descrição                          |
|--------|------------------------|------------------------------------|
| GET    | /api/cardapio          | Lista itens do cardápio            |
| POST   | /api/cardapio          | Cadastra novo item (admin)         |
| PUT    | /api/cardapio/:id      | Edita item (nome e/ou preço)       |
| DELETE | /api/cardapio/:id      | Exclui item do cardápio            |
| GET    | /api/pedidos           | Lista todos os pedidos             |
| GET    | /api/pedidos/:id       | Retorna um pedido (para edição)    |
| POST   | /api/pedidos           | Cria um novo pedido                |
| PUT    | /api/pedidos/:id       | Edita pedido (substitui itens)     |
| DELETE | /api/pedidos/:id       | Exclui pedido                      |

Para mais detalhes sobre o sistema, use o **ROTEIRO.md**.
