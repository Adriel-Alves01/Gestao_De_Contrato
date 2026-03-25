# Gestão de Contratos (CLM)

## O que é este sistema?

O **Gestão de Contratos (CLM)** é uma plataforma completa para gerenciar o ciclo de vida de contratos de forma organizada, segura e rastreável.

Na prática, ele foi criado para que empresas possam **controlar cada etapa de um contrato**: desde o momento em que ele é cadastrado, passando pelo acompanhamento de medições (execução parcial do que foi contratado), até os pagamentos feitos ao fornecedor — tudo com histórico, regras de aprovação e controle por perfil de usuário.

### Para que serve?
- **Gestor de contratos** cadastra e acompanha os contratos, define prazos, valores e partes envolvidas (CNPJ, razão social).
- **Fornecedor** registra as medições (o que foi entregue/executado no período).
- **Financeiro** aprova as medições e processa os pagamentos com emissão de Nota Fiscal.
- **Admin** tem visão total do sistema, gerencia usuários e audita ações.

O sistema também conta com **extração automática de dados via Inteligência Artificial**: ao fazer upload de um PDF de contrato ou nota fiscal, a IA lê o documento e preenche os campos automaticamente, poupando tempo de digitação.

Construído com backend em **Django REST** e frontend em **Next.js**.

## Demo online
- Frontend (Vercel): **https://gestao-de-contrato.vercel.app**
- Backend API base (Render): **https://gestao-de-contrato-api.onrender.com**
- Swagger/OpenAPI: `https://gestao-de-contrato-api.onrender.com/api/docs/`

### Acesso de demonstração
- Usuário: **usuario-teste**
- Senha: **12374test**

> Se o serviço estiver em plano free, o primeiro acesso pode demorar alguns segundos (cold start).

## Stack
- Backend: Django 6 + DRF + SimpleJWT
- Frontend: Next.js 16 + TypeScript + Tailwind/shadcn
- Banco: PostgreSQL (ou SQLite em ambiente local)

## Funcionalidades principais
- CRUD de contratos com fechamento e auditoria
- **Upload de PDF com extração automática de dados via IA** (OpenAI GPT-4o-mini e Google Gemini como fallback)
- Campos de CNPJ e razão social de contratante/contratada nos contratos
- Fluxo de medições (criar, aprovar, rejeitar, reabrir) com datas de início/fim e controle de saldo
- Fluxo de pagamentos com regras de negócio e campos de Nota Fiscal (número, data, valor)
- **Pagamento automático ao aprovar medição**
- Controle por papéis (ADMIN, GESTOR, FINANCEIRO, FORNECEDOR)
- Dashboard com visões por papel, alertas de vencimento e tabela de contratos recentes clicável
- Histórico de status, logs de auditoria e soft delete
- Geração de relatórios em PDF
- API documentada (Swagger/OpenAPI)

## Variáveis de ambiente da IA (opcionais)
- OPENAI_API_KEY -- chave da OpenAI
- GOOGLE_API_KEY -- chave do Google Gemini (fallback automático)
- USE_MOCK_DATA=true -- retorna dados de teste sem consumir API

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
