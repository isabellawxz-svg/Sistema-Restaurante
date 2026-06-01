# Entrega 3 — Mapa de mesas do salão

Esta entrega adiciona o **cadastro de mesas** e o **mapa visual** no salão e no caixa, sincronizado com as **comandas**.

## 1. Modelo de dados

- Tabela **`mesas`**: `numero` (único), `capacidade`, `status` (`livre` | `ocupada` | `reservada`), `id_comanda_ativa` (comanda aberta vinculada).
- Coluna **`comandas.id_mesa`**: vínculo opcional; comandas avulsas (balcão, delivery) continuam só com texto em `mesa`.

Na primeira criação do banco, **`init_db.py`** insere **12 mesas** de exemplo (1 a 12). Bancos já existentes recebem tabelas/colunas via **`ensure_schema()`** em `app.py` e a mesma seed se `mesas` estiver vazia.

## 2. Regras de negócio

| Ação | Comportamento |
|------|----------------|
| Abrir comanda pelo mapa (mesa livre) | POST `/api/comandas` com `id_mesa` → mesa fica **ocupada** |
| Comanda avulsa | POST sem `id_mesa` (campo texto livre, ex.: balcão) |
| Pagar ou excluir comanda vinculada | Mesa volta para **livre** |
| Mesa **reservada** | Não abre comanda até o admin mudar para livre |
| Admin altera status/capacidade | PUT `/api/mesas/<id>`; não altera mesa **ocupada** para livre/reservada enquanto houver comanda aberta |

## 3. Telas

| Rota | Quem | Função |
|------|------|--------|
| `/admin/mesas` | admin | Cadastrar, editar capacidade/status, excluir mesas |
| `/garcom` | admin, garçom | Mapa + comandas (topo da página) |
| `/caixa` | admin, caixa | Mapa + comandas e pagamento |

## 4. API nova

| Método | Rota | Quem |
|--------|------|------|
| GET | `/api/mesas` | admin, caixa, garçom |
| POST | `/api/mesas` | admin |
| PUT | `/api/mesas/<id>` | admin |
| DELETE | `/api/mesas/<id>` | admin |

Resposta de listagem inclui, quando ocupada, resumo da comanda (`id`, `cliente_nome`, `total`, `itens_count`).

**Comandas:** POST aceita opcionalmente `id_mesa` (além de `mesa` / `cliente_nome`). Resposta de comanda inclui `id_mesa`.

## 5. Arquivos principais

| Área | Arquivos |
|------|----------|
| Schema / seed | `init_db.py`, `app.py` (`_ensure_mesas_schema`, `_seed_mesas`, helpers de ocupar/liberar) |
| Admin mesas | `templates/admin/mesas.html`, `static/admin_mesas.js` |
| Mapa salão/caixa | `static/salao_mesas.js`, `templates/garcom.html`, `templates/caixa.html` |
| Modal comanda | `static/comandas_modal.js` (`abrirModalNovaComanda` com `id_mesa`) |
| Estilo | `static/style.css` (`.mapa-mesas-grid`, `.mesa-card--*`) |

## 6. Demonstração sugerida (2–3 min)

1. **Admin** → Mesas do salão: marcar mesa 5 como **reservada**.
2. **Garçom** → Salão: no mapa, clicar mesa **livre** (ex.: 3) → criar comanda → lançar itens no modal.
3. Tentar abrir mesa **5** (reservada) → mensagem de bloqueio.
4. **Caixa** → Clicar mesa **ocupada** (3) → conferir itens → **pagar** → mapa mostra mesa 3 **livre** de novo.
5. Opcional: **Comanda avulsa** para balcão sem usar o mapa.

Roteiro completo do sistema: [ROTEIRO.md](ROTEIRO.md).
