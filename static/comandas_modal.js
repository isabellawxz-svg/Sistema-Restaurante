/**
 * Modal estilo PDV: nova comanda (mesa/cliente) e lançamento de itens.
 * Depende de: apiFetch, escapeHtml, itensCardapio, carregarComandas (app.js)
 */

function _modalRoot() {
    return document.getElementById("modal-comanda-root");
}

function fecharModalComanda() {
    var root = _modalRoot();
    if (!root) return;
    root.style.display = "none";
    root.setAttribute("aria-hidden", "true");
    document.getElementById("modal-comanda-corpo").innerHTML = "";
    document.getElementById("modal-comanda-rodape").innerHTML = "";
}

function abrirModalShell(titulo, corpoHtml, rodapeHtml) {
    var root = _modalRoot();
    if (!root) return;
    document.getElementById("modal-comanda-titulo").textContent = titulo;
    document.getElementById("modal-comanda-corpo").innerHTML = corpoHtml;
    document.getElementById("modal-comanda-rodape").innerHTML = rodapeHtml || "";
    root.style.display = "flex";
    root.setAttribute("aria-hidden", "false");
}

function initModalComandas() {
    var root = _modalRoot();
    if (!root || root.dataset.modalInit) return;
    root.dataset.modalInit = "1";
    root.addEventListener("click", function(ev) {
        var t = ev.target;
        if (t && t.closest && t.closest("[data-fechar-modal]")) fecharModalComanda();
    });
    document.addEventListener("keydown", function(ev) {
        if (ev.key === "Escape" && root.style.display === "flex") fecharModalComanda();
    });
}

function abrirModalNovaComanda() {
    var corpo = "<div class=\"modal-form-grid\">" +
        "<label>Mesa / referência<br><input type=\"text\" id=\"modal-nc-mesa\" maxlength=\"40\" placeholder=\"Ex.: 12, balcão\"></label>" +
        "<label>Cliente (opcional)<br><input type=\"text\" id=\"modal-nc-cliente\" maxlength=\"80\"></label>" +
        "</div><p id=\"modal-nc-msg\" class=\"msg-modal\"></p>";
    var rodape = "<button type=\"button\" class=\"btn-primario\" id=\"modal-nc-criar\">Criar comanda</button>" +
        "<button type=\"button\" class=\"btn-secundario\" data-fechar-modal>Cancelar</button>";
    abrirModalShell("Nova comanda", corpo, rodape);
    document.getElementById("modal-nc-criar").addEventListener("click", async function() {
        var mesa = document.getElementById("modal-nc-mesa").value.trim();
        var cliente = document.getElementById("modal-nc-cliente").value.trim();
        var msg = document.getElementById("modal-nc-msg");
        msg.textContent = "";
        if (!mesa) {
            msg.textContent = "Informe a mesa ou referência.";
            return;
        }
        var res = await apiFetch("/api/comandas", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ mesa: mesa, cliente_nome: cliente })
        });
        if (!res) return;
        var data = await res.json();
        if (!res.ok) {
            msg.textContent = data.erro || "Erro ao criar.";
            return;
        }
        fecharModalComanda();
        carregarComandas();
        abrirModalLancamentoComanda(data.id);
    });
}

async function abrirModalLancamentoComanda(idComanda) {
    var res = await apiFetch("/api/comandas/" + idComanda);
    if (!res) return;
    var comanda = await res.json();
    if (!res.ok) {
        alert(comanda.erro || "Erro ao carregar comanda.");
        return;
    }
    if (!comanda.pode_editar_itens) {
        alert("Esta comanda não aceita mais alterações.");
        return;
    }
    if (!itensCardapio || itensCardapio.length === 0) {
        await carregarCardapio();
    }
    var titulo = "Comanda #" + comanda.id + " — Mesa " + (comanda.mesa || "—");
    var html = "<p class=\"modal-resumo\">Total atual: <strong>R$ " + Number(comanda.total).toFixed(2) + "</strong></p>";
    html += "<div class=\"modal-busca-wrap\"><label class=\"modal-busca-label\">Buscar itens <input type=\"search\" id=\"modal-busca-item\" class=\"modal-busca-input\" placeholder=\"Filtrar pelo nome\" autocomplete=\"off\"></label></div>";
    html += "<div class=\"modal-itens-scroll\" id=\"modal-itens-scroll-root\">";
    var porCat = {};
    itensCardapio.forEach(function(item) {
        var cat = (item.categoria || "").trim() || "Sem categoria";
        if (!porCat[cat]) porCat[cat] = [];
        porCat[cat].push(item);
    });
    var cats = Object.keys(porCat).sort(function(a, b) {
        return a.localeCompare(b, "pt-BR");
    });
    cats.forEach(function(cat) {
        html += "<section class=\"modal-cat-grupo\">";
        html += "<h4 class=\"modal-cat-titulo\">" + escapeHtml(cat) + "</h4>";
        porCat[cat].forEach(function(item) {
            var qtd = 0;
            var linha = (comanda.itens || []).find(function(i) { return i.id_item === item.id; });
            if (linha) qtd = linha.quantidade;
            html += "<div class=\"modal-linha-item\"><label>" + escapeHtml(item.nome) + " <span class=\"preco-mini\">R$ " +
                item.preco.toFixed(2) + "</span></label>" +
                "<input type=\"number\" min=\"0\" class=\"modal-qtd-item\" data-id-item=\"" + item.id + "\" value=\"" + qtd + "\"></div>";
        });
        html += "</section>";
    });
    html += "</div><p id=\"modal-itens-msg\" class=\"msg-modal\"></p>";
    var rodape = "<button type=\"button\" class=\"btn-primario\" id=\"modal-itens-salvar\">Salvar na comanda</button>" +
        "<button type=\"button\" class=\"btn-secundario\" data-fechar-modal>Fechar</button>";
    abrirModalShell(titulo, html, rodape);
    var inpBusca = document.getElementById("modal-busca-item");
    if (inpBusca) {
        inpBusca.addEventListener("input", function() {
            var q = inpBusca.value.trim().toLowerCase();
            document.querySelectorAll(".modal-linha-item").forEach(function(row) {
                var lab = row.querySelector("label");
                var texto = lab ? lab.textContent.toLowerCase() : "";
                var ok = !q || texto.indexOf(q) >= 0;
                row.style.display = ok ? "" : "none";
            });
            document.querySelectorAll(".modal-cat-grupo").forEach(function(sec) {
                var vis = false;
                sec.querySelectorAll(".modal-linha-item").forEach(function(row) {
                    if (row.style.display !== "none") vis = true;
                });
                sec.style.display = vis ? "" : "none";
            });
        });
    }
    document.getElementById("modal-itens-salvar").addEventListener("click", async function() {
        var inputs = document.querySelectorAll(".modal-qtd-item");
        var itens = [];
        inputs.forEach(function(inp) {
            var q = parseInt(inp.value, 10);
            if (q > 0) itens.push({ id_item: parseInt(inp.dataset.idItem, 10), quantidade: q });
        });
        var res2 = await apiFetch("/api/comandas/" + idComanda, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ itens: itens })
        });
        if (!res2) return;
        var data2 = await res2.json();
        if (!res2.ok) {
            document.getElementById("modal-itens-msg").textContent = data2.erro || "Erro ao salvar.";
            return;
        }
        fecharModalComanda();
        carregarComandas();
    });
}
