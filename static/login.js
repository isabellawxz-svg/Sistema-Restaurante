document.getElementById("form-login").addEventListener("submit", async function(ev) {
    ev.preventDefault();
    const login = document.getElementById("login").value.trim();
    const senha = document.getElementById("senha").value;
    const msg = document.getElementById("msg-login");
    msg.textContent = "";
    try {
        const res = await fetch("/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ login: login, senha: senha })
        });
        const data = await res.json();
        if (res.ok && data.redirect) {
            window.location.href = data.redirect;
            return;
        }
        msg.textContent = (data && data.erro) ? data.erro : "Não foi possível entrar.";
    } catch (e) {
        msg.textContent = "Erro de conexão.";
        console.error(e);
    }
});
