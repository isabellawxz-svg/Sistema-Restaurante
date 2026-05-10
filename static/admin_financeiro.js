function _hojeISO() {
    var d = new Date();
    return d.toISOString().slice(0, 10);
}

function _trintaDiasAtras() {
    var d = new Date();
    d.setDate(d.getDate() - 30);
    return d.toISOString().slice(0, 10);
}

var _ultimoResumoFinanceiro = null;
var _ultimoRankingItens = null;

function renderPainelFinanceiro(data) {
    var el = document.getElementById("painel-financeiro");
    if (!el) return;
    var h = "<div class=\"fin-cards\">";
    h += "<div class=\"fin-card\"><h3>Receita (vendas)</h3><p class=\"fin-valor\">R$ " + data.receita_vendas.toFixed(2) + "</p>";
    h += "<p class=\"fin-sub\">" + data.comandas_fechadas + " comandas no período</p></div>";
    h += "<div class=\"fin-card\"><h3>Compras registradas</h3><p class=\"fin-valor\">R$ " + data.compras_registradas_valor.toFixed(2) + "</p>";
    h += "<p class=\"fin-sub\">Soma das notas de compra (lançamento manual)</p></div></div>";
    h += "<h3 class=\"fin-titulo-sec\">Por forma de pagamento</h3><ul class=\"fin-lista-forma\">";
    (data.por_forma_pagamento || []).forEach(function(l) {
        var nome = { dinheiro: "Dinheiro", pix: "PIX", cartao: "Cartão" }[l.forma_pagamento] || l.forma_pagamento;
        h += "<li><strong>" + nome + "</strong>: R$ " + l.total.toFixed(2) + " (" + l.comandas + " comandas)</li>";
    });
    h += "</ul><p class=\"fin-periodo\">Período: " + data.inicio + " a " + data.fim + "</p>";
    el.innerHTML = h;
}

function renderRankingItens(payload) {
    var el = document.getElementById("painel-ranking-itens");
    if (!el) return;
    var itens = (payload && payload.itens) || [];
    if (itens.length === 0) {
        el.innerHTML = "<p class=\"fin-sub\">Nenhuma venda de item no período (comandas pagas).</p>";
        return;
    }
    var tbl = "<table class=\"tabela-admin fin-ranking-tab\"><thead><tr><th>#</th><th>Item</th><th>Qtd</th><th>Receita</th></tr></thead><tbody>";
    itens.forEach(function(row, idx) {
        tbl += "<tr><td>" + (idx + 1) + "</td><td>" + escapeHtml(row.nome) + "</td><td>" + row.quantidade_vendida + "</td>";
        tbl += "<td>R$ " + row.receita.toFixed(2) + "</td></tr>";
    });
    tbl += "</tbody></table>";
    el.innerHTML = tbl;
}

function _nomeArquivoCsv(prefixo) {
    var ini = document.getElementById("fin-inicio");
    var fim = document.getElementById("fin-fim");
    var a = (ini && ini.value) || "";
    var b = (fim && fim.value) || "";
    return prefixo + "-" + a + "_" + b + ".csv";
}

function exportarFinanceiroCsv() {
    if (!_ultimoResumoFinanceiro) {
        alert("Atualize o painel antes de exportar.");
        return;
    }
    var data = _ultimoResumoFinanceiro;
    var rank = _ultimoRankingItens || { itens: [] };
    var linhas = [];
    linhas.push("sep=;");
    linhas.push("Resumo financeiro");
    linhas.push("Início;" + data.inicio);
    linhas.push("Fim;" + data.fim);
    linhas.push("Receita vendas (R$);" + data.receita_vendas.toFixed(2));
    linhas.push("Comandas fechadas;" + data.comandas_fechadas);
    linhas.push("Compras registradas (R$);" + data.compras_registradas_valor.toFixed(2));
    linhas.push("");
    linhas.push("Por forma de pagamento");
    linhas.push("Forma;Total (R$);Comandas");
    (data.por_forma_pagamento || []).forEach(function(l) {
        var nome = { dinheiro: "Dinheiro", pix: "PIX", cartao: "Cartão" }[l.forma_pagamento] || (l.forma_pagamento || "");
        linhas.push(nome + ";" + l.total.toFixed(2) + ";" + l.comandas);
    });
    linhas.push("");
    linhas.push("Ranking de itens (quantidade vendida em comandas pagas)");
    linhas.push("Item;Quantidade;Receita (R$)");
    (rank.itens || []).forEach(function(r) {
        linhas.push("\"" + r.nome.replace(/"/g, '""') + "\";" + r.quantidade_vendida + ";" + r.receita.toFixed(2));
    });
    var csv = linhas.join("\r\n");
    var blob = new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = _nomeArquivoCsv("financeiro");
    a.click();
    URL.revokeObjectURL(a.href);
}

async function atualizarPainelFinanceiro() {
    var ini = document.getElementById("fin-inicio").value || _trintaDiasAtras();
    var fim = document.getElementById("fin-fim").value || _hojeISO();
    var q = "inicio=" + encodeURIComponent(ini) + "&fim=" + encodeURIComponent(fim);
    var res = await apiFetch("/api/financeiro/resumo?" + q);
    if (!res) return;
    var data = await res.json();
    if (!res.ok) {
        document.getElementById("painel-financeiro").innerHTML = "<p class=\"msg-erro\">" + (data.erro || "Erro ao carregar.") + "</p>";
        document.getElementById("painel-ranking-itens").innerHTML = "";
        _ultimoResumoFinanceiro = null;
        _ultimoRankingItens = null;
        return;
    }
    _ultimoResumoFinanceiro = data;
    renderPainelFinanceiro(data);
    var resRank = await apiFetch("/api/financeiro/ranking-itens?" + q + "&limit=20");
    if (!resRank) return;
    var rankData = await resRank.json();
    if (!resRank.ok) {
        document.getElementById("painel-ranking-itens").innerHTML = "<p class=\"msg-erro\">" + (rankData.erro || "Erro no ranking.") + "</p>";
        _ultimoRankingItens = null;
        return;
    }
    _ultimoRankingItens = rankData;
    renderRankingItens(rankData);
}

document.addEventListener("DOMContentLoaded", function() {
    var btn = document.getElementById("btn-fin-atualizar");
    var btnCsv = document.getElementById("btn-fin-csv");
    if (!btn) return;
    document.getElementById("fin-fim").value = _hojeISO();
    document.getElementById("fin-inicio").value = _trintaDiasAtras();
    btn.addEventListener("click", atualizarPainelFinanceiro);
    if (btnCsv) btnCsv.addEventListener("click", exportarFinanceiroCsv);
    atualizarPainelFinanceiro();
});
