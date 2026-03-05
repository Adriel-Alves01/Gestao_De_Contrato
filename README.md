# Gestão de Contratos (CLM)

Sistema de **Contract Lifecycle Management** com backend em Django REST e frontend em Next.js.

## Demo online
- Frontend (Vercel): **https://gestao-de-contrato.vercel.app**
- Backend API base (Render): **https://gestao-de-contrato-api.onrender.com**
- Swagger/OpenAPI: `https://gestao-de-contrato-api.onrender.com/api/docs/`

### Acesso de demonstração
- Usuário: **Usuario_Teste**
- Senha: **Teste124**

> Se o serviço estiver em plano free, o primeiro acesso pode demorar alguns segundos (cold start).

## Stack
- Backend: Django 6 + DRF + SimpleJWT
- Frontend: Next.js 16 + TypeScript + Tailwind/shadcn
- Banco: PostgreSQL (ou SQLite em ambiente local)

## Funcionalidades principais
- CRUD de contratos com fechamento e auditoria
- Fluxo de medições (criar, aprovar, rejeitar, reabrir)
- Fluxo de pagamentos com regras de negócio
- **Pagamento automático ao aprovar medição**
- Controle por papéis (ADMIN, GESTOR, FINANCEIRO, FORNECEDOR)
- Dashboard com visões por papel
- API documentada (Swagger/OpenAPI)

## Estrutura do projeto
- `core/` configuração Django
- `contracts/` domínio principal (contratos, medições, pagamentos)
- `frontend/` aplicação web Next.js

## Como rodar localmente

### 1) Backend
```bash
cd C:\dev\GestaoContrato
C:/dev/GestaoContrato/venv/Scripts/python.exe manage.py migrate
C:/dev/GestaoContrato/venv/Scripts/python.exe manage.py runserver
```

Backend em: `http://localhost:8000`

### 2) Frontend
```bash
cd C:\dev\GestaoContrato\frontend
npm install
npm run dev
```

Frontend em: `http://localhost:3000`

## Variáveis de ambiente
- Backend: copie `.env.example` para `.env` (ou configure no provedor de deploy)
- Frontend: copie `frontend/.env.example` para `frontend/.env.local`

## Qualidade

### Backend
```bash
cd C:\dev\GestaoContrato
C:/dev/GestaoContrato/venv/Scripts/python.exe manage.py check
C:/dev/GestaoContrato/venv/Scripts/python.exe -m pytest
```

### Frontend
```bash
cd C:\dev\GestaoContrato\frontend
npm run build
```

## Deploy (resumo)
- Frontend: Vercel
- Backend: Render 
- Banco: PostgreSQL gerenciado
- Configurar variáveis no provedor

## Observações
- Projeto com regras de negócio reais (RBAC + auditoria + fluxo financeiro)
- Testes automatizados cobrindo cenários de sucesso e erro
- Interface web com foco em operação por perfil
