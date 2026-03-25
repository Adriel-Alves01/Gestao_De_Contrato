import json
import os
import re
import random
from typing import Any, Dict, Optional

from pypdf import PdfReader

import openai
import google.genai as genai


class ClaudeExtractionError(Exception):
    """Erro ao extrair dados do contrato via IA."""


def _extract_json_payload(text: str) -> Dict[str, Any]:
    """Tenta extrair um objeto JSON de uma string de resposta."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find('{')
    end = text.rfind('}')
    if start == -1 or end == -1 or end <= start:
        raise ClaudeExtractionError(
            "Não foi possível localizar JSON na resposta da IA"
        )

    candidate = text[start:end + 1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ClaudeExtractionError(
            "Resposta da IA não contém JSON válido"
        ) from exc


def _normalize_date(value: Optional[str]) -> Optional[str]:
    if not value:
        return None

    value = value.strip()
    patterns = [
        r"^(\d{4})-(\d{2})-(\d{2})$",
        r"^(\d{2})/(\d{2})/(\d{4})$",
        r"^(\d{2})\.(\d{2})\.(\d{4})$",
    ]

    for pat in patterns:
        m = re.match(pat, value)
        if not m:
            continue

        if pat.startswith("^(\\d{4})"):
            year, month, day = m.groups()
        else:
            day, month, year = m.groups()

        try:
            return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
        except ValueError:
            return None

    try:
        return str(__import__("datetime").date.fromisoformat(value))
    except Exception:
        return None


def _normalize_money(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text:
        return None

    text = re.sub(r"[R$\s]", "", text)

    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", ".")

    try:
        return float(text)
    except ValueError:
        return None


def extract_contract_data_from_pdf(file_obj) -> Dict[str, Any]:
    """Extrai dados de um contrato a partir de um PDF usando IA.

    Retorna um dict com os campos:
      - title
      - description
      - start_date (YYYY-MM-DD)
      - end_date (YYYY-MM-DD)
      - total_value (float)
      - parties (opcional)
    """

    # Lê texto do PDF
    reader = PdfReader(file_obj)
    text_parts = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        text_parts.append(page_text)
        if sum(len(p) for p in text_parts) > 18_000:
            break
    text = "\n".join(text_parts)

    # Tenta usar OpenAI primeiro, depois Google Gemini como fallback
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    USE_MOCK_DATA = os.getenv('USE_MOCK_DATA', 'false').lower() == 'true'

    # Se USE_MOCK_DATA está ativado, pula direto para mock
    if USE_MOCK_DATA:
        completion_text = _extract_mock_data(text)
        extracted = _extract_json_payload(completion_text)
        return {
            "title": extracted.get("title") or None,
            "description": extracted.get("description") or None,
            "start_date": _normalize_date(extracted.get("start_date")),
            "end_date": _normalize_date(extracted.get("end_date")),
            "total_value": _normalize_money(extracted.get("total_value")),
            "parties": extracted.get("parties") or None,
            "numero_contrato": extracted.get("numero_contrato") or "",
            "empresa_contratante": (
                extracted.get("empresa_contratante") or None
            ),
            "empresa_contratada": extracted.get("empresa_contratada") or None,
            "cnpj_empresa_contratada": (
                extracted.get("cnpj_empresa_contratada") or None
            ),
            "cnpj_empresa_contratante": (
                extracted.get("cnpj_empresa_contratante") or None
            ),
        }

    prompt = f"""
Você é um especialista em análise jurídica e extração de dados de contratos.

PASSO 1: Identifique as partes do contrato
Analise o contrato e identifique claramente:
1. Quem é a empresa CONTRATANTE (quem está contratando o serviço)
2. Quem é a empresa CONTRATADA (quem executa o serviço)

Regras para identificação:
- CONTRATANTE: quem está solicitando/contratando o serviço
  (aparece como "de um lado" ou primeira parte mencionada)
- CONTRATADA: quem executa o serviço
  (aparece como "de outro lado" ou segunda parte mencionada)
- Se não tiver certeza absoluta, retorne null

PASSO 2: Extraia TODOS os dados solicitados
Responda SOMENTE com um objeto JSON válido, sem comentários adicionais.

Se não conseguir encontrar um valor, use null.
Para CNPJ: "CNPJ nº", "inscrita sob o CNPJ", "CNPJ:", etc.
Para datas: converta para formato YYYY-MM-DD
Para valor: extraia números, removendo símbolos de moeda

CAMPOS OBRIGATÓRIOS NO JSON:
{{
  "title": "título principal do contrato",
  "description": "descrição breve do objeto/serviço",
  "start_date": "data de início em YYYY-MM-DD ou null",
  "end_date": "data de término em YYYY-MM-DD ou null",
  "total_value": "valor total como número ou null",
  "numero_contrato": "número/identificação do contrato ou null",
  "empresa_contratante": "nome completo da empresa contratante ou null",
  "cnpj_empresa_contratante": "CNPJ contratante XX.XXX.XXX/XXXX-XX ou null",
  "empresa_contratada": "nome completo da empresa contratada ou null",
  "cnpj_empresa_contratada": "CNPJ contratada XX.XXX.XXX/XXXX-XX ou null",
  "parties": "lista de todas as partes envolvidas (opcional)"
}}

CONTRATO:
{text}"""

    import logging as _logging
    if OPENAI_API_KEY:
        try:
            completion_text = _extract_with_openai(text, OPENAI_API_KEY)
        except Exception as e:
            _logging.exception(f"[AI] OpenAI falhou: {e}")
            # Fallback para Gemini se OpenAI falhar
            if GOOGLE_API_KEY and GOOGLE_API_KEY != 'your-google-api-key-here':
                try:
                    client = genai.Client(api_key=GOOGLE_API_KEY)
                    response = client.models.generate_content(
                        model='models/gemini-2.5-flash',
                        contents=prompt
                    )
                    completion_text = response.text
                except Exception as e2:
                    _logging.exception(f"[AI] Gemini falhou: {e2}")
                    raise ClaudeExtractionError(
                        f"OpenAI falhou ({e}) e Gemini falhou ({e2}). "
                        "Configure OPENAI_API_KEY ou GOOGLE_API_KEY."
                    )
            else:
                raise ClaudeExtractionError(
                    f"OpenAI falhou: {e}. "
                    "Configure OPENAI_API_KEY ou GOOGLE_API_KEY no servidor."
                )
    elif GOOGLE_API_KEY and GOOGLE_API_KEY != 'your-google-api-key-here':
        try:
            client = genai.Client(api_key=GOOGLE_API_KEY)
            response = client.models.generate_content(
                model='models/gemini-2.5-flash',
                contents=prompt
            )
            completion_text = response.text
        except Exception as e:
            _logging.exception(f"[AI] Gemini falhou: {e}")
            raise ClaudeExtractionError(
                f"Gemini falhou: {e}. Configure GOOGLE_API_KEY corretamente."
            )
    else:
        raise ClaudeExtractionError(
            "Nenhuma API configurada. "
            "Defina OPENAI_API_KEY ou GOOGLE_API_KEY no servidor."
        )

    extracted = _extract_json_payload(completion_text)

    return {
        "title": extracted.get("title") or None,
        "description": extracted.get("description") or None,
        "start_date": _normalize_date(extracted.get("start_date")),
        "end_date": _normalize_date(extracted.get("end_date")),
        "total_value": _normalize_money(extracted.get("total_value")),
        "parties": extracted.get("parties") or None,
        "numero_contrato": extracted.get("numero_contrato") or "",
        "empresa_contratante": extracted.get("empresa_contratante") or None,
        "empresa_contratada": extracted.get("empresa_contratada") or None,
        "cnpj_empresa_contratada": (
            extracted.get("cnpj_empresa_contratada") or None
        ),
        "cnpj_empresa_contratante": (
            extracted.get("cnpj_empresa_contratante") or None
        ),
    }


def _extract_with_openai(text, api_key):
    """Extrai dados usando OpenAI como primária."""
    os.environ.pop('HTTP_PROXY', None)
    os.environ.pop('HTTPS_PROXY', None)
    os.environ.pop('http_proxy', None)
    os.environ.pop('https_proxy', None)

    client = openai.OpenAI(api_key=api_key)

    messages = [
        {
            "role": "system",
            "content": (
                "Você é um assistente que extrai informações de contratos."
                " Responda apenas com um único objeto JSON válido."
            ),
        },
        {
            "role": "user",
            "content": f"""
Você é um especialista em análise jurídica e extração de dados de contratos.

PASSO 1: Identifique as partes do contrato
Analise o contrato e identifique claramente:
1. Quem é a empresa CONTRATANTE (quem está contratando o serviço)
2. Quem é a empresa CONTRATADA (quem executa o serviço)

Regras para identificação:
- CONTRATANTE: quem está solicitando/contratando o serviço
  (aparece como "de um lado" ou primeira parte mencionada)
- CONTRATADA: quem executa o serviço
  (aparece como "de outro lado" ou segunda parte mencionada)
- Se não tiver certeza absoluta, retorne null

PASSO 2: Extraia TODOS os dados solicitados
Responda SOMENTE com um objeto JSON válido, sem comentários adicionais.

Se não conseguir encontrar um valor, use null.
Para CNPJ: "CNPJ nº", "inscrita sob o CNPJ", "CNPJ:", etc.
Para datas: converta para formato YYYY-MM-DD
Para valor: extraia números, removendo símbolos de moeda

CAMPOS OBRIGATÓRIOS NO JSON:
{{
  "title": "título principal do contrato",
  "description": "descrição breve do objeto/serviço",
  "start_date": "data de início em YYYY-MM-DD ou null",
  "end_date": "data de término em YYYY-MM-DD ou null",
  "total_value": "valor total como número ou null",
  "numero_contrato": "número/identificação do contrato ou null",
  "empresa_contratante": "nome completo da empresa contratante ou null",
  "cnpj_empresa_contratante": "CNPJ contratante XX.XXX.XXX/XXXX-XX ou null",
  "empresa_contratada": "nome completo da empresa contratada ou null",
  "cnpj_empresa_contratada": "CNPJ contratada XX.XXX.XXX/XXXX-XX ou null",
  "parties": "lista de todas as partes envolvidas (opcional)"
}}

CONTRATO:
{text}"""
        }
    ]

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=1200,
        temperature=0.1
    )

    return completion.choices[0].message.content


def _extract_mock_data(text):
    """Retorna dados mockados quando nenhuma API está configurada."""
    mock_responses = [
        {
            "title": "Contrato de Prestação de Serviços",
            "description": (
                "Acordo para desenvolvimento e implementação de sistema"
                " de gestão [DADOS DE TESTE - Configure GOOGLE_API_KEY"
                " para usar IA real]"
            ),
            "start_date": "2024-03-01",
            "end_date": "2024-12-31",
            "total_value": 75000.00,
            "parties": ["Empresa Contratante Ltda", "Empresa Prestadora S.A."],
            "numero_contrato": "CTR-2024-001",
            "empresa_contratante": "Empresa Contratante Ltda",
            "empresa_contratada": "Empresa Prestadora S.A.",
            "cnpj_empresa_contratante": "11.222.333/0001-44",
            "cnpj_empresa_contratada": "12.345.678/0001-90"
        },
        {
            "title": "Acordo de Parceria Comercial",
            "description": (
                "Parceria estratégica para distribuição de produtos"
                " [DADOS DE TESTE - Configure GOOGLE_API_KEY"
                " para usar IA real]"
            ),
            "start_date": "2024-01-15",
            "end_date": "2025-01-14",
            "total_value": 150000.00,
            "parties": ["Distribuidora XYZ", "Fabricante ABC Ltda"],
            "numero_contrato": "PRT-2024-045",
            "empresa_contratante": "Distribuidora XYZ Ltda",
            "empresa_contratada": "Fabricante ABC Ltda",
            "cnpj_empresa_contratante": "22.333.444/0001-55",
            "cnpj_empresa_contratada": "98.765.432/0001-10"
        },
        {
            "title": "Contrato de Locação",
            "description": (
                "Locação de imóvel comercial para escritório"
                " [DADOS DE TESTE - Configure GOOGLE_API_KEY"
                " para usar IA real]"
            ),
            "start_date": "2024-04-01",
            "end_date": "2025-03-31",
            "total_value": 24000.00,
            "parties": ["Locador Imóveis Ltda", "Inquilino Comércio S.A."],
            "numero_contrato": "LOC-2024-012",
            "empresa_contratante": "Locador Imóveis Ltda",
            "empresa_contratada": "Inquilino Comércio S.A.",
            "cnpj_empresa_contratante": "33.444.555/0001-66",
            "cnpj_empresa_contratada": "11.222.333/0001-44"
        }
    ]

    selected = random.choice(mock_responses)
    return json.dumps(selected, ensure_ascii=False)



# Extração de Nota Fiscal


def extract_nf_data(file_obj) -> Dict[str, Any]:
    """Extrai dados de uma Nota Fiscal (PDF ou imagem) usando IA.

    Retorna um dict com:
      - numero_nota_fiscal  (str ou None)
      - data_emissao_nota   (YYYY-MM-DD ou None)
      - valor_nota_fiscal   (float ou None)
    """
    # Lê o PDF; se falhar, usa texto bruto (pypdf não suporta imagens)
    text = ""
    try:
        reader = PdfReader(file_obj)
        parts = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
            if sum(len(p) for p in parts) > 10_000:
                break
        text = "\n".join(parts)
    except Exception:
        text = ""

    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
    USE_MOCK_DATA = os.getenv('USE_MOCK_DATA', 'false').lower() == 'true'

    nf_prompt = f"""Você é especialista em Notas Fiscais brasileiras.

Extraia os seguintes campos da Nota Fiscal abaixo e responda
SOMENTE com um objeto JSON válido:

{{
  "numero_nota_fiscal": "número da NF (apenas dígitos/alfanumérico) ou null",
  "data_emissao_nota": "data de emissão no formato YYYY-MM-DD ou null",
  "valor_nota_fiscal": "valor total da NF como número (sem símbolo R$) ou null"
}}

NOTA FISCAL:
{text or "(arquivo sem texto extraível)"}"""

    completion_text = None

    no_api_key = (
        not GOOGLE_API_KEY
        or GOOGLE_API_KEY == 'your-google-api-key-here'
    )
    if USE_MOCK_DATA or (not OPENAI_API_KEY and no_api_key):
        completion_text = json.dumps({
            "numero_nota_fiscal": "NF-0001",
            "data_emissao_nota": "2026-03-01",
            "valor_nota_fiscal": 5000.00,
        })
    elif OPENAI_API_KEY:
        try:
            os.environ.pop('HTTP_PROXY', None)
            os.environ.pop('HTTPS_PROXY', None)
            os.environ.pop('http_proxy', None)
            os.environ.pop('https_proxy', None)
            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Você extrai dados de Notas Fiscais."
                            " Responda apenas com JSON válido."
                        ),
                    },
                    {"role": "user", "content": nf_prompt},
                ],
                max_tokens=300,
                temperature=0.1,
            )
            completion_text = resp.choices[0].message.content
        except Exception:
            completion_text = None

    google_valid = (
        GOOGLE_API_KEY
        and GOOGLE_API_KEY != 'your-google-api-key-here'
    )
    if completion_text is None and google_valid:
        try:
            from_client = genai.Client(api_key=GOOGLE_API_KEY)
            response = from_client.models.generate_content(
                model='models/gemini-2.5-flash',
                contents=nf_prompt,
            )
            completion_text = response.text
        except Exception:
            completion_text = None

    _empty: Dict[str, Any] = {
        "numero_nota_fiscal": None,
        "data_emissao_nota": None,
        "valor_nota_fiscal": None,
    }
    if completion_text is None:
        return _empty

    try:
        extracted = _extract_json_payload(completion_text)
    except ClaudeExtractionError:
        return _empty

    return {
        "numero_nota_fiscal": extracted.get("numero_nota_fiscal") or None,
        "data_emissao_nota": (
            _normalize_date(extracted.get("data_emissao_nota"))
        ),
        "valor_nota_fiscal": (
            _normalize_money(extracted.get("valor_nota_fiscal"))
        ),
    }
