# Entrega 1 — Núcleo pedagógico

Esta entrega corresponde ao **primeiro ciclo** do projeto, focado em mostrar como **banco de dados**, **backend** e **frontend** se conectam em um sistema pequeno e compreensível.

## Objetivos de aprendizagem

- Modelar dados em **SQLite** (tabelas, chaves, leitura e gravação).
- Expor um **backend** em **Flask** com rotas e respostas **JSON**.
- Construir **páginas HTML** com **JavaScript** usando **`fetch`** para consumir a API.
- Praticar operações de **CRUD** sobre entidades centrais do domínio (no ciclo inicial: **cardápio** e **pedidos** anotados na mesma ideia de “consumo no salão”).

## O que foi contemplado (conceito da entrega 1)

1. **Banco (SQLite)**  
   - Arquivo único (`dados.db`).  
   - Tabelas para **itens do cardápio** e estrutura de **pedidos** (cabeçalho + itens), como exemplo clássico de **1:N** (um pedido, várias linhas de item).

2. **Backend (Flask)**  
   - Rotas para listar e alterar o **cardápio**.  
   - Rotas para **criar, listar, editar e excluir pedidos**, retornando JSON para o front.

3. **Frontend**  
   - Página principal com **lista do cardápio** e forma de **registrar pedidos**.  
   - Página (ou seção) de **administração** para **cadastrar / editar / excluir** itens do cardápio.  
   - Navegação simples (por exemplo barra de links no topo), sem preocupação ainda com **papéis de usuário** ou **estoque**.

4. **Documentação e reprodutibilidade**  
   - `README` com **como instalar** dependências, **criar o banco** (`init_db.py`) e **subir o servidor** (`app.py`).  
   - Lista resumida das rotas da API para consulta rápida.

## Stack fixada na entrega 1

| Camada   | Escolha |
|----------|---------|
| Banco    | SQLite |
| Backend  | Python 3 + Flask |
| Frontend | HTML, CSS, JavaScript (sem React/Vue, etc.) |

## Relação com o código atual

O repositório **evoluiu** após a entrega 1: o domínio de **pedidos** foi substituído/estendido por **comandas**, **login**, **papéis**, **estoque** e outras telas (ver **README_ENTREGA_2.md**).  
A entrega 1 permanece válida como **marco conceitual**: mesmo com mais tabelas e rotas hoje, o núcleo “**API + SQLite + páginas com fetch**” é o mesmo fio condutor.

## Critérios típicos de avaliação (entrega 1)

- Subir o projeto e acessar as telas sem erro.  
- Demonstrar **persistência** no SQLite após recarregar a página.  
- Explicar **uma rota GET** e **uma rota POST ou PUT** olhando o código.  
- Explicar **como o front chama a API** (URL, método, tratamento da resposta).
