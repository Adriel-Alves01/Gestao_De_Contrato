# 📚 Documentação da API - CLM (Contract Lifecycle Management)

## 🚀 Acessando a Documentação

A API possui **documentação interativa completa** gerada automaticamente via Swagger/OpenAPI.

### 1️⃣ Iniciar o Servidor

```bash
python manage.py runserver
```

### 2️⃣ Acessar a Documentação

Abra o navegador em uma das URLs:

#### **Swagger UI** (Recomendado)
```
http://localhost:8000/api/docs/
```
- Interface interativa moderna
- Teste endpoints direto no navegador
- Visualização clara de schemas

#### **ReDoc** (Alternativa)
```
http://localhost:8000/api/redoc/
```
- Documentação estilo "livro"
- Ideal para leitura e referência
- Layout mais limpo e focado

#### **Schema OpenAPI (JSON)**
```
http://localhost:8000/api/schema/
```
- Especificação OpenAPI 3.0 em JSON
- Para integração com ferramentas externas
- Geração de clientes automáticos

---

## 📋 O Que Está Documentado

### **Contratos** (`/api/contracts/`)
- ✅ Listagem e detalhes
- ✅ Criação e atualização
- ✅ Soft delete (remoção lógica)
- ✅ Fechamento de contrato
- ✅ Histórico de status

### **Medições** (`/api/measurements/`)
- ✅ Listagem e detalhes
- ✅ Criação
- ✅ Aprovação
- ✅ Rejeição

### **Pagamentos** (`/api/payments/`)
- ✅ Listagem e detalhes
- ✅ Criação
- ✅ Marcar como pago (atualiza saldo)
- ✅ Marcar como falho

---

## 🔐 Autenticação

A API agora suporta **dois modos** de autenticação:

- **Session Auth** (cookies): ideal para Django Admin e testes manuais no browser.
- **JWT (Bearer Token)**: ideal para frontend Next.js (App Router), SPA e mobile.

### JWT (recomendado para frontend Next.js)

Endpoints:

```
POST /api/token/
POST /api/token/refresh/
POST /api/token/verify/
```

Exemplo para obter tokens:

```json
POST /api/token/
{
   "username": "seu_usuario",
   "password": "sua_senha"
}
```

Resposta:

```json
{
   "refresh": "<refresh_token>",
   "access": "<access_token>"
}
```

Uso no header das chamadas protegidas:

```
Authorization: Bearer <access_token>
```

Para testar endpoints protegidos no Swagger:

1. **Faça login via Session Auth:**
   ```
   http://localhost:8000/api-auth/login/
   ```
   - Digite seu username e senha
   - Clique em "Log in"
   - **Você será redirecionado automaticamente para o Swagger!**

2. **Agora você está autenticado! 🔒**
   - O cadeado no Swagger deve estar fechado
   - Pode testar todos os endpoints protegidos

3. **Para sair (fazer logout):**
   ```
   http://localhost:8000/logout/
   ```
   - Você será redirecionado automaticamente para o Swagger
   - Agora está deslogado

### ⚠️ **Nota sobre o botão "Authorize"**

Agora o botão **Authorize** no Swagger pode ser usado com JWT:

- Gere token em `/api/token/`
- Clique em **Authorize**
- Informe: `Bearer <access_token>`

Session Auth continua disponível via `/api-auth/login/`.

---

## 🎯 Recursos da Documentação

### **Para Desenvolvedores Frontend:**
- 📄 Estrutura completa de todos os JSONs (request/response)
- 🔍 Campos obrigatórios e opcionais claramente marcados
- ✅ Validações e possíveis erros documentados
- 🎮 Teste interativo de todos os endpoints
- 📋 Exemplos de requisições e respostas

### **Para Integração:**
- 📦 Schema OpenAPI 3.0 compatível com qualquer ferramenta
- 🔄 Geração automática de clientes (Python, JavaScript, etc)
- 📚 Documentação sempre atualizada (é gerada do código)

---

## 📊 Informações na Documentação

Para cada endpoint, você encontra:

✅ **Método HTTP** (GET, POST, PUT, DELETE)  
✅ **URL completa** com parâmetros  
✅ **Descrição detalhada** da operação  
✅ **Permissões** necessárias (quais roles podem acessar)  
✅ **Request Body** com estrutura JSON completa  
✅ **Response** com exemplos reais  
✅ **Códigos de Status** (200, 400, 403, 404, etc)  
✅ **Validações** e regras de negócio  
✅ **Exemplos** prontos para copiar e usar  

---

## 🛡️ Regras de Permissão (RBAC)

A documentação mostra claramente quem pode fazer o quê:

| Role | Contratos | Medições | Pagamentos |
|------|-----------|----------|------------|
| **SUPER** | ✅ Tudo | ✅ Tudo | ✅ Tudo |
| **ADMIN** | ✅ Tudo | ✅ Tudo | ✅ Tudo |
| **GESTOR** | ✅ Apenas seus | ✅ Aprovar/Rejeitar | ❌ Apenas leitura |
| **FINANCEIRO** | 👁️ Apenas leitura | 👁️ Apenas leitura | ✅ Criar/Marcar pago |
| **FORNECEDOR** | 👁️ Apenas leitura | 👁️ Apenas leitura | 👁️ Apenas leitura |

---

## 🎨 Exemplo de Uso

### 1. Abra o Swagger
```
http://localhost:8000/api/docs/
```

### 2. Expanda um Endpoint
Clique em **POST /api/contracts/** para ver detalhes

### 3. Clique em "Try it out"
Habilita edição dos campos

### 4. Preencha os Dados
```json
{
  "title": "Contrato Teste Swagger",
  "description": "Criado via documentação interativa",
  "total_value": "50000.00",
  "start_date": "2026-01-01",
  "end_date": "2026-12-31"
}
```

### 5. Clique em "Execute"
Faz a requisição REAL na API!

### 6. Veja a Resposta
```json
{
  "id": 10,
  "title": "Contrato Teste Swagger",
  "status": "ACTIVE",
  "remaining_balance": "50000.00",
  ...
}
```

---

## 🔧 Configuração Técnica

A documentação é gerada automaticamente por:

- **drf-spectacular**: Melhor lib de OpenAPI para Django REST
- **OpenAPI 3.0**: Padrão da indústria
- **Swagger UI**: Interface interativa
- **ReDoc**: Documentação legível

Toda a configuração está em:
- `core/settings.py` → `SPECTACULAR_SETTINGS`
- `core/urls.py` → URLs de documentação
- `contracts/views.py` → Docstrings das views

---

## 📝 Atualizando a Documentação

**A documentação é automática!** Sempre que você:

- ✅ Adiciona um novo endpoint
- ✅ Modifica campos de um serializer
- ✅ Muda permissões
- ✅ Atualiza docstrings

A documentação **se atualiza sozinha** na próxima vez que acessar!

Não precisa escrever nada manualmente. 🎉

---

## 🌐 URLs Úteis

| URL | Descrição |
|-----|-----------|
| `http://localhost:8000/api/docs/` | Swagger UI (interativo) |
| `http://localhost:8000/api/redoc/` | ReDoc (leitura) |
| `http://localhost:8000/api/schema/` | OpenAPI Schema (JSON) |
| `http://localhost:8000/api/` | API raiz |
| `http://localhost:8000/api/token/` | Obter JWT (access + refresh) |
| `http://localhost:8000/api/token/refresh/` | Renovar access token |
| `http://localhost:8000/api/token/verify/` | Validar token |
| `http://localhost:8000/api-auth/login/` | Login (Session Auth) |
| `http://localhost:8000/logout/` | Logout (Session Auth) |
| `http://localhost:8000/admin/` | Django Admin |

---

## 🎯 Próximos Passos

Agora que tem documentação completa:

1. ✅ **Frontend** pode ser desenvolvido consultando `/api/docs/`
2. ✅ **Integrações** podem usar o schema OpenAPI
3. ✅ **Testes manuais** podem ser feitos via Swagger
4. ✅ **Onboarding** de novos devs é instantâneo

---

**🚀 API Pronta para Produção!**
