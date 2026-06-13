#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monitor DJEN - OAB PI 16818
Busca publicações via PJe API, classifica por urgência,
envia relatório por e-mail (Gmail SMTP) e WhatsApp (CallMeBot).
"""

import os
import sys
import re
import smtplib
import requests
from datetime import date, datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ---------------------------------------------------------------------------
# CONFIGURAÇÕES (via variáveis de ambiente / GitHub Secrets)
# ---------------------------------------------------------------------------
OAB_NUMERO   = "16818"
OAB_UF       = "PI"
API_URL      = (
    f"https://comunicaapi.pje.jus.br/api/v1/comunicacao"
    f"?numeroOab={OAB_NUMERO}&ufOab={OAB_UF}"
)

EMAIL_DEST   = "joselucasportelaadv@gmail.com"
EMAIL_FROM   = os.environ.get("GMAIL_USER", "")
EMAIL_PASS   = os.environ.get("GMAIL_PASS", "")

# CallMeBot WhatsApp – cadastre em https://www.callmebot.com/blog/free-api-whatsapp-messages/
WA_PHONE     = "5586995670741"
WA_APIKEY    = os.environ.get("CALLMEBOT_APIKEY", "")

HOJE = date.today()

# ---------------------------------------------------------------------------
# FERIADOS NACIONAIS FIXOS (ano corrente)
# ---------------------------------------------------------------------------
def feriados_nacionais(ano: int) -> set:
    return {
        date(ano, 1, 1),    # Confraternização Universal
        date(ano, 4, 21),   # Tiradentes
        date(ano, 5, 1),    # Dia do Trabalho
        date(ano, 9, 7),    # Independência
        date(ano, 10, 12),  # N. Sra. Aparecida
        date(ano, 11, 2),   # Finados
        date(ano, 11, 15),  # Proclamação da República
        date(ano, 12, 25),  # Natal
    }


FERIADOS = feriados_nacionais(HOJE.year) | feriados_nacionais(HOJE.year + 1)


def dias_uteis_restantes(data_limite: date) -> int:
    """Conta dias úteis entre hoje (exclusive) e data_limite (inclusive)."""
    if data_limite < HOJE:
        return 0
    count = 0
    d = HOJE + timedelta(days=1)
    while d <= data_limite:
        if d.weekday() < 5 and d not in FERIADOS:
            count += 1
        d += timedelta(days=1)
    return count


def classificar_urgencia(dias: int) -> str:
    if dias == 0:
        return "URGENTISSIMO – PRAZO HOJE"
    elif dias <= 2:
        return "CRITICO"
    elif dias <= 5:
        return "URGENTE"
    elif dias <= 10:
        return "ATENCAO"
    else:
        return "NORMAL"


# ---------------------------------------------------------------------------
# BUSCA NA API
# ---------------------------------------------------------------------------
def buscar_publicacoes() -> list:
    try:
        resp = requests.get(API_URL, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", []) if isinstance(data, dict) else data
        return items if isinstance(items, list) else []
    except Exception as e:
        print(f"Erro ao buscar publicacoes: {e}", file=sys.stderr)
        return []


# ---------------------------------------------------------------------------
# PARSER DE PUBLICAÇÃO
# ---------------------------------------------------------------------------
def parse_publicacao(item: dict) -> dict:
    texto       = item.get("texto", "") or ""
    data_disp   = item.get("data_disponibilizacao", "") or ""
    numero_proc = item.get("numero_processo", "") or ""
    tipo_doc    = item.get("tipoDocumento", "") or ""
    nome_classe = item.get("nomeClasse", "") or ""
    link        = item.get("link", "") or ""
    sigla_trib  = item.get("siglaTribunal", "") or ""
    nome_orgao  = item.get("nomeOrgao", "") or ""

    # Extrai datas do texto (dd/mm/aaaa)
    datas_texto = re.findall(r"(\d{2}/\d{2}/\d{4})", texto)
    data_prazo  = None
    for ds in datas_texto:
        try:
            d = datetime.strptime(ds, "%d/%m/%Y").date()
            if d >= HOJE:
                data_prazo = d
                break
        except ValueError:
            pass

    # Data de disponibilização
    try:
        dt_disp = datetime.fromisoformat(data_disp[:10]).date() if data_disp else None
    except Exception:
        dt_disp = None

    dias     = dias_uteis_restantes(data_prazo) if data_prazo else None
    urgencia = classificar_urgencia(dias) if dias is not None else "SEM PRAZO IDENTIFICADO"

    return {
        "numero_processo": numero_proc,
        "tribunal":        sigla_trib,
        "orgao":           nome_orgao,
        "tipo_documento":  tipo_doc,
        "classe":          nome_classe,
        "data_disponibilizacao": str(dt_disp) if dt_disp else data_disp[:10] if data_disp else "—",
        "data_prazo":      str(data_prazo) if data_prazo else "Nao identificada",
        "dias_uteis":      dias,
        "urgencia":        urgencia,
        "texto_resumo":    texto[:500].replace("\n", " "),
        "link":            link,
    }


# ---------------------------------------------------------------------------
# FORMATAÇÃO DO RELATÓRIO
# ---------------------------------------------------------------------------
URGENCIA_EMOJI = {
    "URGENTISSIMO – PRAZO HOJE": "🔴",
    "CRITICO":  "🔴",
    "URGENTE":  "🟠",
    "ATENCAO":  "🟡",
    "NORMAL":   "🟢",
    "SEM PRAZO IDENTIFICADO": "⚪",
}


def formatar_relatorio_html(publicacoes: list) -> str:
    linhas = []
    for i, p in enumerate(publicacoes, 1):
        emoji    = URGENCIA_EMOJI.get(p["urgencia"], "⚪")
        dias_str = str(p["dias_uteis"]) if p["dias_uteis"] is not None else "—"
        link_html = f'<a href="{p["link"]}">Ver</a>' if p["link"] else "—"
        linhas.append(
            f"<tr><td>{i}</td>"
            f"<td><b>{emoji} {p['urgencia']}</b></td>"
            f"<td>{dias_str}</td>"
            f"<td>{p['numero_processo']}</td>"
            f"<td>{p['tribunal']} / {p['orgao']}</td>"
            f"<td>{p['tipo_documento']}</td>"
            f"<td>{p['data_prazo']}</td>"
            f"<td><small>{p['texto_resumo'][:300]}...</small></td>"
            f"<td>{link_html}</td></tr>"
        )

    return f"""<html><body>
<h2>📋 DJEN Monitor – OAB PI {OAB_NUMERO} – {HOJE.strftime('%d/%m/%Y')}</h2>
<p>Total de publicações encontradas: <b>{len(publicacoes)}</b></p>
<table border="1" cellpadding="5" cellspacing="0"
       style="border-collapse:collapse;font-size:13px;">
  <thead style="background:#2c3e50;color:white;">
    <tr>
      <th>#</th><th>Urgência</th><th>Dias Úteis</th>
      <th>Processo</th><th>Tribunal/Órgão</th><th>Tipo</th>
      <th>Prazo</th><th>Resumo</th><th>Link</th>
    </tr>
  </thead>
  <tbody>{''.join(linhas)}</tbody>
</table>
<br>
<p style="color:gray;font-size:11px;">
  Gerado automaticamente via GitHub Actions – DJEN Monitor
</p>
</body></html>"""


def formatar_relatorio_texto(publicacoes: list) -> str:
    linhas = [
        f"DJEN Monitor – OAB PI {OAB_NUMERO} – {HOJE.strftime('%d/%m/%Y')}",
        f"Total: {len(publicacoes)} publicacao(oes)\n",
    ]
    for i, p in enumerate(publicacoes, 1):
        dias_str = str(p["dias_uteis"]) if p["dias_uteis"] is not None else "?"
        linhas.append(
            f"{i}. [{p['urgencia']}]\n"
            f"   Processo : {p['numero_processo']}\n"
            f"   Tribunal : {p['tribunal']} / {p['orgao']}\n"
            f"   Prazo    : {p['data_prazo']} ({dias_str} dias uteis)\n"
            f"   Resumo   : {p['texto_resumo'][:250]}...\n"
        )
    return "\n".join(linhas)


def formatar_whatsapp(publicacoes: list) -> str:
    if not publicacoes:
        return (
            f"📭 DJEN {HOJE.strftime('%d/%m/%Y')}: "
            f"Nenhuma publicacao para OAB PI {OAB_NUMERO} hoje."
        )
    criticos = [
        p for p in publicacoes
        if p["urgencia"] in ("URGENTISSIMO – PRAZO HOJE", "CRITICO")
    ]
    msg = [
        f"⚖️ DJEN {HOJE.strftime('%d/%m/%Y')} – OAB PI {OAB_NUMERO}",
        f"📌 {len(publicacoes)} publicacao(oes) encontrada(s).",
    ]
    if criticos:
        msg.append(f"🚨 {len(criticos)} com prazo CRITICO:")
        for p in criticos[:3]:
            dias_str = str(p["dias_uteis"]) if p["dias_uteis"] is not None else "?"
            msg.append(f"  • {p['numero_processo']} – {p['urgencia']} ({dias_str} dias uteis)")
    msg.append("Verifique o e-mail para o relatorio completo.")
    return "\n".join(msg)


# ---------------------------------------------------------------------------
# ENVIO DE E-MAIL
# ---------------------------------------------------------------------------
def enviar_email(assunto: str, html: str, texto: str):
    if not EMAIL_FROM or not EMAIL_PASS:
        print("⚠  Credenciais Gmail nao configuradas (GMAIL_USER / GMAIL_PASS).")
        return
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = assunto
        msg["From"]    = EMAIL_FROM
        msg["To"]      = EMAIL_DEST
        msg.attach(MIMEText(texto, "plain", "utf-8"))
        msg.attach(MIMEText(html,  "html",  "utf-8"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_FROM, EMAIL_PASS)
            server.sendmail(EMAIL_FROM, EMAIL_DEST, msg.as_string())
        print(f"✅ E-mail enviado para {EMAIL_DEST}")
    except Exception as e:
        print(f"❌ Erro ao enviar e-mail: {e}", file=sys.stderr)


# ---------------------------------------------------------------------------
# ENVIO DE WHATSAPP VIA CALLMEBOT
# ---------------------------------------------------------------------------
def enviar_whatsapp(mensagem: str):
    if not WA_APIKEY:
        print("⚠  CALLMEBOT_APIKEY nao configurado – WhatsApp nao enviado.")
        return
    try:
        url    = "https://api.callmebot.com/whatsapp.php"
        params = {"phone": WA_PHONE, "text": mensagem, "apikey": WA_APIKEY}
        resp   = requests.get(url, params=params, timeout=20)
        if resp.status_code == 200:
            print(f"✅ WhatsApp enviado para {WA_PHONE}")
        else:
            print(f"❌ Falha WhatsApp: {resp.status_code} – {resp.text[:200]}", file=sys.stderr)
    except Exception as e:
        print(f"❌ Erro WhatsApp: {e}", file=sys.stderr)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    print(f"🔍 Buscando publicacoes DJEN para OAB PI {OAB_NUMERO}...")
    items = buscar_publicacoes()

    # Filtra publicações do dia de hoje
    hoje_str            = HOJE.isoformat()
    publicacoes_hoje    = [
        item for item in items
        if (item.get("data_disponibilizacao") or "").startswith(hoje_str)
    ]

    print(
        f"📄 {len(publicacoes_hoje)} publicacao(oes) para hoje "
        f"({HOJE.strftime('%d/%m/%Y')})."
    )

    if not publicacoes_hoje:
        assunto = (
            f"DJEN {HOJE.strftime('%d/%m/%Y')} – "
            f"Sem publicacoes para OAB PI {OAB_NUMERO}"
        )
        html  = (
            f"<html><body>"
            f"<h3>📭 Sem publicacoes no DJEN hoje "
            f"({HOJE.strftime('%d/%m/%Y')}) para OAB PI {OAB_NUMERO}.</h3>"
            f"</body></html>"
        )
        texto  = (
            f"Sem publicacoes no DJEN hoje "
            f"({HOJE.strftime('%d/%m/%Y')}) para OAB PI {OAB_NUMERO}."
        )
        wa_msg = (
            f"📭 DJEN {HOJE.strftime('%d/%m/%Y')}: "
            f"Nenhuma publicacao para OAB PI {OAB_NUMERO} hoje."
        )
    else:
        parsed = [parse_publicacao(item) for item in publicacoes_hoje]
        parsed.sort(key=lambda p: p["dias_uteis"] if p["dias_uteis"] is not None else 9999)

        assunto = (
            f"DJEN {HOJE.strftime('%d/%m/%Y')} – "
            f"{len(parsed)} publicacao(oes) | OAB PI {OAB_NUMERO}"
        )
        html   = formatar_relatorio_html(parsed)
        texto  = formatar_relatorio_texto(parsed)
        wa_msg = formatar_whatsapp(parsed)

    enviar_email(assunto, html, texto)
    enviar_whatsapp(wa_msg)
    print("✅ Monitoramento concluido.")


if __name__ == "__main__":
    main()
