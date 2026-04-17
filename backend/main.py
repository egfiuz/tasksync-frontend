import os
from fastapi import FastAPI, HTTPException, status, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone


# Imports do Google Auth e Firestore
from google.oauth2 import id_token
from google.auth.transport import requests
from google.cloud import firestore

# --- CONFIGURAÇÃO DO BANCO DE DADOS ---
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "serviceAccountKey.json"
db = firestore.Client()

app = FastAPI(title="TaskSync API")

GOOGLE_CLIENT_ID = "648909581862-92hjjltj6udot3rff8quvuf3lke6vtan.apps.googleusercontent.com"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TokenAuth(BaseModel):
    token: str

@app.get("/")
def home():
    return {"status": "online", "projeto": "TaskSync"}

@app.post("/auth/google")
async def google_login(data: TokenAuth):
    if not data.token:
        raise HTTPException(status_code=400, detail="Token não fornecido")
    try:
        idinfo = id_token.verify_oauth2_token(data.token, requests.Request(), GOOGLE_CLIENT_ID)
        email_do_aluno = idinfo['email']
        nome_do_aluno = idinfo['name']
        
        aluno_ref = db.collection("alunos").document(email_do_aluno)
        aluno_doc = aluno_ref.get()

        print("\n" + "="*50)
        if not aluno_doc.exists:
            print(f"🆕 NOVO ALUNO: Criando perfil no Firestore para {nome_do_aluno}...")
            aluno_ref.set({
                "nome": nome_do_aluno,
                "email": email_do_aluno,
                "curso": "ADS - FATEC",
                "data_cadastro": firestore.SERVER_TIMESTAMP,
                "ultimo_acesso": firestore.SERVER_TIMESTAMP
            })
        else:
            print(f"🏠 BEM-VINDA DE VOLTA: Atualizando acesso de {nome_do_aluno}...")
            aluno_ref.update({
                "ultimo_acesso": firestore.SERVER_TIMESTAMP
            })
        print("="*50 + "\n")

        return {
            "status": "sucesso",
            "mensagem": f"Login concluído e dados sincronizados para {nome_do_aluno}!"
        }

    except ValueError:
        raise HTTPException(status_code=401, detail="Token inválido")
    except Exception as e:
        print(f"Erro no banco de dados: {e}")
        raise HTTPException(status_code=500, detail="Erro interno no servidor")
    
# --- ROTAS DE TAREFAS ---
class NovaTarefa(BaseModel):
    token: str
    titulo: str
    descricao: str
    disciplina: str
    data_entrega: str

class ConcluirTarefa(BaseModel):
    token: str

@app.post("/tarefas")
async def criar_tarefa(dados: NovaTarefa):
    try:
        idinfo = id_token.verify_oauth2_token(dados.token, requests.Request(), GOOGLE_CLIENT_ID)
        email_do_aluno = idinfo['email']

        tarefa_doc = {
            "titulo": dados.titulo,
            "descricao": dados.descricao,
            "disciplina": dados.disciplina,
            "data_entrega": dados.data_entrega,
            "status": "pendente",
            "criado_em": firestore.SERVER_TIMESTAMP
        }

        db.collection("alunos").document(email_do_aluno).collection("tarefas").add(tarefa_doc)
        print(f"✅ TAREFA SALVA: '{dados.titulo}' guardada na pasta de {email_do_aluno}")
        return {"status": "sucesso", "mensagem": "Tarefa sincronizada com sucesso!"}

    except ValueError:
        raise HTTPException(status_code=401, detail="Crachá inválido ou expirado.")
    except Exception as e:
        print(f"Erro ao salvar tarefa: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao salvar no banco.")
    
@app.get("/tarefas")
async def listar_tarefas(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Crachá não fornecido ou inválido.")
    token = authorization.split("Bearer ")[1]
    try:
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), GOOGLE_CLIENT_ID)
        email_do_aluno = idinfo['email']

        tarefas_ref = db.collection("alunos").document(email_do_aluno).collection("tarefas")
        docs = tarefas_ref.order_by("criado_em", direction=firestore.Query.DESCENDING).stream()
        
        lista_de_tarefas = []
        for doc in docs:
            tarefa = doc.to_dict()
            tarefa["id"] = doc.id
            tarefa.pop("criado_em", None) 
            lista_de_tarefas.append(tarefa)

        print(f"📖 LEITURA: Foram encontradas {len(lista_de_tarefas)} tarefas para {email_do_aluno}")
        return {"status": "sucesso", "tarefas": lista_de_tarefas}

    except ValueError:
        raise HTTPException(status_code=401, detail="Crachá inválido ou expirado.")
    except Exception as e:
        print(f"Erro ao buscar tarefas: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao ler do banco.")

@app.delete("/tarefas/{tarefa_id}")
async def apagar_tarefa(tarefa_id: str, authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Crachá não fornecido.")
    token = authorization.split("Bearer ")[1]
    try:
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), GOOGLE_CLIENT_ID)
        email_do_aluno = idinfo['email']

        doc_ref = db.collection("alunos").document(email_do_aluno).collection("tarefas").document(tarefa_id)
        doc_ref.delete()
        print(f"🗑️ EXCLUSÃO: Tarefa {tarefa_id} apagada por {email_do_aluno}")
        return {"status": "sucesso", "mensagem": "Tarefa excluída com sucesso!"}

    except ValueError:
        raise HTTPException(status_code=401, detail="Crachá inválido.")
    except Exception as e:
        print(f"Erro ao excluir tarefa: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao excluir.")

@app.put("/tarefas/{tarefa_id}")
async def atualizar_tarefa(tarefa_id: str, dados: NovaTarefa):
    try:
        idinfo = id_token.verify_oauth2_token(dados.token, requests.Request(), GOOGLE_CLIENT_ID)
        email_do_aluno = idinfo['email']

        doc_ref = db.collection("alunos").document(email_do_aluno).collection("tarefas").document(tarefa_id)
        doc_ref.update({
            "titulo": dados.titulo,
            "descricao": dados.descricao,
            "disciplina": dados.disciplina,
            "data_entrega": dados.data_entrega
        })
        print(f"✏️ ATUALIZAÇÃO: Tarefa {tarefa_id} editada por {email_do_aluno}")
        return {"status": "sucesso", "mensagem": "Entrega atualizada com sucesso no banco!"}

    except ValueError:
        raise HTTPException(status_code=401, detail="Crachá inválido ou expirado.")
    except Exception as e:
        print(f"Erro ao atualizar: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao atualizar.")

@app.patch("/tarefas/{tarefa_id}/concluir")
async def concluir_tarefa(tarefa_id: str, dados: ConcluirTarefa):
    try:
        # 1. Verifica o crachá do Google
        idinfo = id_token.verify_oauth2_token(dados.token, requests.Request(), GOOGLE_CLIENT_ID)
        email_do_aluno = idinfo['email']

        # 2. Captura o momento exato em que o botão foi clicado
        agora = datetime.now(timezone.utc)

        # 3. Localiza a tarefa exata do aluno no Firestore
        tarefa_ref = db.collection("alunos").document(email_do_aluno).collection("tarefas").document(tarefa_id)
        
        # 4. Atualiza o status e injeta a métrica final para a IA
        tarefa_ref.update({
            "status": "concluido",
            "data_conclusao": agora.isoformat() 
        })

        print(f"✅ TAREFA CONCLUÍDA: ID {tarefa_id} finalizada por {email_do_aluno}")
        return {"status": "sucesso", "mensagem": "Missão cumprida e dados registrados!"}

    except ValueError:
        raise HTTPException(status_code=401, detail="Crachá inválido ou expirado.")
    except Exception as e:
        print(f"Erro ao concluir tarefa: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao atualizar o banco.")

# --- ROTAS DO MURAL DE AVISOS (BOLETINS) ---
class NovoBoletim(BaseModel):
    token: str
    conteudo: str

@app.post("/boletins")
async def criar_boletim(dados: NovoBoletim):
    try:
        idinfo = id_token.verify_oauth2_token(dados.token, requests.Request(), GOOGLE_CLIENT_ID)
        email_do_aluno = idinfo['email']

        # Definimos que o aviso expira em 7 dias (o TTL que configuraremos no Google)
        data_expiracao = datetime.now() + timedelta(days=7)

        boletim_doc = {
            "conteudo": dados.conteudo,
            "autor": idinfo['name'],
            "criado_em": firestore.SERVER_TIMESTAMP,
            "expira_em": data_expiracao
        }

        db.collection("alunos").document(email_do_aluno).collection("boletins").add(boletim_doc)
        return {"status": "sucesso", "mensagem": "Aviso publicado no Mural!"}
    except Exception as e:
        print(f"Erro no mural: {e}")
        raise HTTPException(status_code=500, detail="Erro ao publicar aviso.")

@app.get("/boletins")
async def listar_boletins(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Crachá não fornecido.")
    token = authorization.split("Bearer ")[1]
    
    try:
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), GOOGLE_CLIENT_ID)
        email_do_aluno = idinfo['email']

        boletins_ref = db.collection("alunos").document(email_do_aluno).collection("boletins")
        docs = boletins_ref.order_by("criado_em", direction=firestore.Query.DESCENDING).stream()
        
        lista = []
        for doc in docs:
            item = doc.to_dict()
            item.pop("expira_em", None) 
            item.pop("criado_em", None)
            lista.append(item)
        
        return {"boletins": lista}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erro ao listar mural.")