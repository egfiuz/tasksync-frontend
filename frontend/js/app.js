let tokenGlobal = "";
let idTarefaEmEdicao = null;

async function handleCredentialResponse(response) {
    const tokenJWT = response.credential;
    try {
        const apiResponse = await fetch("http://127.0.0.1:8000/auth/google", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ token: tokenJWT })
        });
        const result = await apiResponse.json();

        if (apiResponse.ok) {
            tokenGlobal = tokenJWT; 
            document.getElementById('area_login').style.display = 'none';
            document.getElementById('painel_tarefas').style.display = 'block';
            document.getElementById('mensagem_boas_vindas').innerText = result.mensagem;
            carregarTarefas(); 
        } else {
            alert("Erro no backend: " + result.detail);
        }
    } catch (error) {
        alert("Não consegui falar com o servidor. Verifique o terminal.");
    }
}

document.getElementById('form_tarefa').addEventListener('submit', async function(evento) {
    evento.preventDefault(); 
    const pacoteDaTarefa = {
        token: tokenGlobal,
        titulo: document.getElementById('titulo').value,
        disciplina: document.getElementById('disciplina').value,
        descricao: document.getElementById('descricao').value,
        data_entrega: document.getElementById('data_entrega').value
    };

    let url = "http://127.0.0.1:8000/tarefas";
    let metodo = "POST";

    if (idTarefaEmEdicao) {
        url = `http://127.0.0.1:8000/tarefas/${idTarefaEmEdicao}`;
        metodo = "PUT";
    }

    try {
        const resposta = await fetch(url, {
            method: metodo,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(pacoteDaTarefa)
        });
        const resultado = await resposta.json();

        if (resposta.ok) {
            alert("✅ " + resultado.mensagem);
            document.getElementById('form_tarefa').reset(); 
            idTarefaEmEdicao = null;
            document.querySelector('#form_tarefa button').innerText = "Salvar Tarefa";
            document.querySelector('#form_tarefa button').style.backgroundColor = "var(--azul-neon)";
            carregarTarefas();
        } else {
            alert("❌ Erro ao salvar: " + resultado.detail);
        }
    } catch (erro) {
        alert("Erro na comunicação com o servidor.");
    }
});

async function carregarTarefas() {
    try {
        const resposta = await fetch("http://127.0.0.1:8000/tarefas", {
            method: "GET",
            headers: { "Authorization": "Bearer " + tokenGlobal }
        });
        const resultado = await resposta.json();
        const container = document.getElementById('container_tarefas');

        if (resposta.ok) {
            container.innerHTML = ""; 
            if (resultado.tarefas.length === 0) {
                container.innerHTML = "<p style='font-style: italic;'>Nenhuma tarefa pendente. Você está em dia!</p>";
                return;
            }

            resultado.tarefas.forEach(tarefa => {
                const cartao = document.createElement('div');
                cartao.className = "cartao-tarefa"; 
                const dataFormatada = new Date(tarefa.data_entrega).toLocaleDateString('pt-BR', {timeZone: 'UTC'});

                cartao.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: start;">
                        <h4 class="cartao-titulo">${tarefa.titulo}</h4>
                        <div>
                            <button onclick="prepararEdicao('${tarefa.id}', '${tarefa.titulo}', '${tarefa.disciplina}', '${tarefa.descricao.replace(/\n/g, '\\n')}', '${tarefa.data_entrega}')" style="background: none; border: none; cursor: pointer; font-size: 18px; padding: 0; margin-right: 12px; filter: grayscale(0.2);" title="Editar tarefa">✏️</button>
                            <button onclick="deletarTarefa('${tarefa.id}')" style="background: none; border: none; cursor: pointer; font-size: 18px; padding: 0; filter: grayscale(0.2);" title="Excluir tarefa">🗑️</button>
                        </div>
                    </div>
                    <p class="cartao-meta">📚 ${tarefa.disciplina} | 📅 Entrega: ${dataFormatada}</p>
                    <p class="cartao-desc">${tarefa.descricao}</p>
                `;
                container.appendChild(cartao);
            });
        }
    } catch (erro) {
        console.error("Falha na conexão:", erro);
    }
}

async function deletarTarefa(idDaTarefa) {
    if (!confirm("Tem certeza que deseja excluir esta entrega?")) return; 
    try {
        const resposta = await fetch(`http://127.0.0.1:8000/tarefas/${idDaTarefa}`, {
            method: "DELETE",
            headers: { "Authorization": "Bearer " + tokenGlobal }
        });
        if (resposta.ok) carregarTarefas();
    } catch (erro) {
        console.error("Falha ao deletar:", erro);
    }
}

function prepararEdicao(id, titulo, disciplina, descricao, data_entrega) {
    idTarefaEmEdicao = id;
    document.getElementById('titulo').value = titulo;
    document.getElementById('disciplina').value = disciplina;
    document.getElementById('descricao').value = descricao;
    document.getElementById('data_entrega').value = data_entrega;
    
    document.querySelector('#form_tarefa button').innerText = "Atualizar Tarefa";
    document.querySelector('#form_tarefa button').style.backgroundColor = "#fbbc05"; 
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// --- FUNÇÕES DO MURAL ---
function toggleMural() {
    const mural = document.getElementById('mural_sidebar');
    if (mural.style.right === "0px") {
        mural.style.right = "-350px";
    } else {
        mural.style.right = "0px";
        carregarMural(); 
    }
}

// COLE ESTA NOVA VERSÃO:
async function postarNoMural() {
    const texto = document.getElementById('texto_boletim').value;
    
    // 1. Verifica se digitou algo
    if (!texto) {
        alert("⚠️ Escreva algo antes de postar!");
        return;
    }

    // 2. Verifica se o aluno fez login após atualizar a página
    if (!tokenGlobal) {
        alert("❌ Crachá ausente! Faça o login do Google novamente na tela inicial.");
        return;
    }

    try {
        const res = await fetch("http://127.0.0.1:8000/boletins", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ token: tokenGlobal, conteudo: texto })
        });
        
        // Pega a resposta do Python
        const resultado = await res.json();

        if (res.ok) {
            document.getElementById('texto_boletim').value = "";
            carregarMural();
            alert("✅ Aviso postado com sucesso no Firestore!");
        } else {
            alert("❌ O Backend recusou: " + resultado.detail);
        }
    } catch (e) { 
        console.error("Erro ao postar mural:", e);
        alert("🔌 Falha de conexão! O seu terminal com o Uvicorn (Python) está rodando?");
    }
}
async function carregarMural() {
    try {
        const res = await fetch("https://tasksync-api-648909581862.southamerica-east1.run.app", {
            method: "GET",
            headers: { "Authorization": "Bearer " + tokenGlobal }
        });
        const data = await res.json();
        const container = document.getElementById('container_boletins');
        container.innerHTML = "";

        data.boletins.forEach(b => {
            const div = document.createElement('div');
            div.style.cssText = "background: var(--fundo-input); padding: 12px; border-radius: 10px; border: 1px solid var(--borda);";
            div.innerHTML = `
                <p style="margin: 0 0 5px 0; font-size: 14px; color: var(--texto-principal);">${b.conteudo}</p>
                <small style="color: var(--azul-neon); font-size: 11px;">📢 Por: ${b.autor}</small>
            `;
            container.appendChild(div);
        });
    } catch (e) { console.error("Erro ao carregar mural:", e); }
}