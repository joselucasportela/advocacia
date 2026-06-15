import csv
import smtplib
import os
import requests
from datetime import date, datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

DATAJUD_URL = "https://api-publica.datajud.cnj.jus.br"
# Chave pública disponibilizada pelo CNJ para uso da API pública
DATAJUD_API_KEY = "cDZHYzlZa0JadVREZDJCendFbXNBR3A6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw=="

TRIBUNAL_INDEX = {
    'TJSP': 'api_publica_tjsp', 'TJRJ': 'api_publica_tjrj', 'TJMG': 'api_publica_tjmg',
    'TJRS': 'api_publica_tjrs', 'TJPR': 'api_publica_tjpr', 'TJSC': 'api_publica_tjsc',
    'TJBA': 'api_publica_tjba', 'TJPE': 'api_publica_tjpe', 'TJCE': 'api_publica_tjce',
    'TJGO': 'api_publica_tjgo', 'TJMA': 'api_publica_tjma', 'TJMT': 'api_publica_tjmt',
    'TJMS': 'api_publica_tjms', 'TJPA': 'api_publica_tjpa', 'TJPB': 'api_publica_tjpb',
    'TJAL': 'api_publica_tjal', 'TJRN': 'api_publica_tjrn', 'TJSE': 'api_publica_tjse',
    'TJPI': 'api_publica_tjpi', 'TJAM': 'api_publica_tjam', 'TJRO': 'api_publica_tjro',
    'TJAC': 'api_publica_tjac', 'TJAP': 'api_publica_tjap', 'TJRR': 'api_publica_tjrr',
    'TJTO': 'api_publica_tjto', 'TJDF': 'api_publica_tjdft',
    'TRT1': 'api_publica_trt1', 'TRT2': 'api_publica_trt2', 'TRT3': 'api_publica_trt3',
    'TRT4': 'api_publica_trt4', 'TRT15': 'api_publica_trt15', 'TRT18': 'api_publica_trt18',
    'STJ': 'api_publica_stj', 'STF': 'api_publica_stf',
    'TRF1': 'api_publica_trf1', 'TRF2': 'api_publica_trf2', 'TRF3': 'api_publica_trf3',
    'TRF4': 'api_publica_trf4', 'TRF5': 'api_publica_trf5', 'TRF6': 'api_publica_trf6',
}


def load_processos(filepath):
    with open(filepath, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def numero_apenas_digitos(numero):
    return ''.join(filter(str.isdigit, numero))


def query_datajud(numero_processo, tribunal):
    index = TRIBUNAL_INDEX.get(tribunal.upper())
    if not index:
        index = f"api_publica_{tribunal.lower()}"

    url = f"{DATAJUD_URL}/{index}/_search"
    headers = {
        'Authorization': f'ApiKey {DATAJUD_API_KEY}',
        'Content-Type': 'application/json',
    }
    payload = {
        "query": {"match": {"numeroProcesso": numero_apenas_digitos(numero_processo)}},
        "sort": [{"dataHoraUltimaAtualizacao": {"order": "desc"}}],
        "size": 1,
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=20)
        resp.raise_for_status()
        hits = resp.json().get('hits', {}).get('hits', [])
        return hits[0].get('_source', {}) if hits else None
    except Exception as e:
        print(f"Erro ao consultar DataJud [{numero_processo}]: {e}")
        return None


def movimentos_recentes(processo_data, dias=7):
    if not processo_data:
        return []

    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=dias)
    recentes = []

    for mov in processo_data.get('movimentos', []):
        data_str = mov.get('dataHora', '')
        try:
            if data_str.endswith('Z'):
                data_str = data_str[:-1] + '+00:00'
            dt = datetime.fromisoformat(data_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt >= cutoff:
                compl = ''
                complementos = mov.get('complementosTabelados', [])
                if complementos:
                    compl = complementos[0].get('nome', '')
                recentes.append({
                    'data': dt.astimezone(timezone(timedelta(hours=-3))).strftime('%d/%m/%Y %H:%M'),
                    'nome': mov.get('nome', 'Sem descrição'),
                    'complemento': compl,
                })
        except (ValueError, TypeError):
            pass

    return recentes


def build_email_body(resultados):
    today = date.today()
    com_mov = [r for r in resultados if r['movimentos']]
    sem_mov = [r for r in resultados if not r['movimentos'] and r['dados']]
    nao_encontrados = [r for r in resultados if r['dados'] is None]

    body = f"""<html><body>
<h2>&#128203; Monitor DataJud &mdash; {today.strftime('%d/%m/%Y')}</h2>
<p>Processos monitorados: <b>{len(resultados)}</b> | Com movimenta&ccedil;&otilde;es nos &uacute;ltimos 7 dias: <b>{len(com_mov)}</b></p>
"""

    if com_mov:
        body += "<h3 style='color:#1e8449'>&#10003; Processos com Movimenta&ccedil;&otilde;es Recentes</h3>"
        for r in com_mov:
            dados = r['dados']
            classe = dados.get('classe', {}).get('nome', 'N/A') if dados else 'N/A'
            assuntos = dados.get('assuntos', []) if dados else []
            assunto = assuntos[0].get('nome', 'N/A') if assuntos else 'N/A'
            body += (
                f"<h4 style='margin-bottom:2px'>{r['numero_processo']} &mdash; {r['cliente']} ({r['tribunal']})</h4>"
                f"<p style='margin-top:2px;color:#555'><i>Classe: {classe} | Assunto: {assunto}</i></p>"
            )
            body += "<ul>"
            for mov in r['movimentos']:
                desc = mov['nome']
                if mov['complemento']:
                    desc += f" &mdash; {mov['complemento']}"
                body += f"<li><b>{mov['data']}</b> &mdash; {desc}</li>"
            body += "</ul>"

    if sem_mov:
        body += "<h3 style='color:#7f8c8d'>&#128193; Sem Movimenta&ccedil;&otilde;es nos &Uacute;ltimos 7 Dias</h3><ul>"
        for r in sem_mov:
            ultima = r['dados'].get('dataHoraUltimaAtualizacao', 'N/A') if r['dados'] else 'N/A'
            body += f"<li>{r['numero_processo']} &mdash; {r['cliente']} | &Uacute;ltima atualiza&ccedil;&atilde;o: {ultima}</li>"
        body += "</ul>"

    if nao_encontrados:
        body += "<h3 style='color:#c0392b'>&#10007; N&atilde;o Encontrados no DataJud</h3><ul>"
        for r in nao_encontrados:
            body += f"<li>{r['numero_processo']} &mdash; {r['cliente']} ({r['tribunal']})</li>"
        body += "</ul>"

    body += "<hr><p><small>Monitor autom&aacute;tico DataJud &mdash; Advocacia</small></p></body></html>"
    return body


def send_email(body, to_email, gmail_user, gmail_pass):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"[Advocacia] Monitor DataJud — {date.today().strftime('%d/%m/%Y')}"
    msg['From'] = gmail_user
    msg['To'] = to_email
    msg.attach(MIMEText(body, 'html', 'utf-8'))

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(gmail_user, gmail_pass)
        server.sendmail(gmail_user, to_email, msg.as_string())


def main():
    gmail_user = os.environ['GMAIL_USER']
    gmail_pass = os.environ['GMAIL_PASS']
    to_email = 'joselucasportelaadv@gmail.com'

    processos = load_processos('data/processos.csv')
    resultados = []

    for p in processos:
        tribunal = p['tribunal'].strip().upper()
        dados = query_datajud(p['numero_processo'].strip(), tribunal)
        movimentos = movimentos_recentes(dados)
        resultados.append({
            'numero_processo': p['numero_processo'].strip(),
            'cliente': p['cliente'].strip(),
            'tribunal': tribunal,
            'dados': dados,
            'movimentos': movimentos,
        })

    body = build_email_body(resultados)
    send_email(body, to_email, gmail_user, gmail_pass)
    com_mov = sum(1 for r in resultados if r['movimentos'])
    print(f"Monitor DataJud enviado. {len(processos)} processos | {com_mov} com movimentacoes recentes.")


if __name__ == '__main__':
    main()
