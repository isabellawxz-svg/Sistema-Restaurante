# Roteiro do sistema — comandas e gestão

Visão geral alinhada ao código atual. Detalhes de API, entregas e como rodar estão em [README.md](README.md), [README_ENTREGA_1.md](README_ENTREGA_1.md) e [README_ENTREGA_2.md](README_ENTREGA_2.md).

## Arquitetura

O sistema tem três camadas: **SQLite** (`dados.db`), **Flask** (`app.py`, porta 5000) e **front** em HTML/CSS/JS com templates Jinja2 (`templates/`, `static/`).

- **Autenticação:** sessão Flask; papéis **admin**, **caixa** e **garçom** definem o que cada usuário vê no menu lateral (`templates/_sidebar_staff.html`).
- **Operação:** **comandas** (mesa/referência, cliente opcional) substituem o modelo antigo de “pedidos soltos”. Itens são lançados por um **modal** estilo PDV (`static/comandas_modal.js`).
- **Estoque:** **insumos** com quantidade; **notas de compra** entram estoque; **composição** (ficha técnica) por item do cardápio. Ao **pagar** a comanda, o sistema baixa insumos e pode bloquear se faltar estoque.
- **Financeiro:** resumo por período (receita de comandas quitadas, compras registradas) e relatórios complementares na própria aplicação.

## Fluxo típico na demonstração

1. Acesse **`/login`** (primeira vez: usuário `admin` / `admin123` se o banco não tinha usuários — troque em uso real).
2. **Admin:** cadastre ou confira **insumos**, **notas de compra**, **receitas** (composição dos pratos) e **cardápio** (itens, preços e categorias).
3. **Garçom:** na tela **Salão**, abra comanda e **lance itens** no modal.
4. **Caixa:** **pague** a comanda (forma de pagamento), conferindo baixa de estoque.
5. **Financeiro** (admin ou caixa): intervalo de datas, totais e exportação quando disponível.

## API (resumo)

Todas as rotas **`/api/*`** exigem sessão autenticada; permissões por rota estão descritas no README e implementadas em `app.py` (`@staff_required`).

Inclui, entre outras: **`/api/cardapio`**, **`/api/comandas`** (CRUD e **`PATCH .../pagamento`**), **`/api/insumos`**, **`/api/notas-compra`**, **`/api/cardapio/<id>/composicao`**, **`/api/financeiro/resumo`**, além de endpoints de **dashboard** e **ranking de itens** usados na visão geral e no financeiro.

## Onde está cada coisa no código

| Área | Arquivos principais |
|------|---------------------|
| Rotas e regras | `app.py` |
| Layout e telas | `templates/`, especialmente `layout_admin.html`, `layout_operacional.html`, `admin/*.html` |
| Comandas e modal | `static/app.js`, `static/comandas_modal.js` |
| Estilo | `static/style.css` |

O caminho completo de uma venda é: **tela → API Flask → SQLite → API → tela atualizada**.
