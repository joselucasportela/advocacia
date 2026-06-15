import smtplib
import os
import requests
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

FEEDS = {
    'STF — Informativo': 'https://portal.stf.jus.br/rss/informativo.asp',
    'STF — Plenário': 'https://portal.stf.jus.br/rss/noticiaspleno.asp',
    'STJ — Informativos': 'https://www.stj.jus.br/sites/portalp/Inicio/rss-feed/informativo-stj',
    'STJ — Notícias': 'https://www.stj.jus.br/sites/portalp/Inicio/rss-feed/ultimas-noticias',
    'CNJ — Notícias': 'https://www.cnj.jus.br/feed/',
}

KEYWORDS_RELEVANTES = [
    'prescrição', 'decadência', 'honorários', 'dano moral', 'repetitivo',
    'repercussão geral', 'tema', 'súmula', 'FGTS', 'trabalhista', 'locação',
    'alimentos', 'prisão', 'tutela', 'execução', 'penhora', 'INSS', 'benefício',
    'consumidor', 'contrato', 'responsabilidade civil', 'indenização',
]


def parse_date(date_str):
    if not date_str:
        return None
    fmts = [
        '%a, %d %b %Y %H:%M:%S %z',
        '%a, %d %b %Y %H:%M:%S GMT',
        '%Y-%m-%dT%H:%M:%S%z',
        '%Y-%m-%dT%H:%M:%SZ',
    ]
    for fmt in fmts:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            pass
    return None


def fetch_feed(nome, url, dias=7):
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=dias)
    itens = []
    try:
        resp = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0 (advocacia-monitor/1.0)'})
        resp.raise_for_status()
        root = ET.fromstring(resp.content)

        ns = ''
        for item in root.iter('item'):
            titulo = item.findtext('title', '').strip()
            link = item.findtext('link', '').strip()
            descricao = item.findtext('description', '').strip()
            pub_date_str = item.findtext('pubDate', '') or item.findtext('{http://purl.org/dc/elements/1.1/}date', '')
            pub_date = parse_date(pub_date_str)

            if pub_date and pub_date < cutoff:
                continue

            texto = (titulo + ' ' + descricao).lower()
            relevante = any(kw.lower() in texto for kw in KEYWORDS_RELEVANTES)

            itens.append({
                'titulo': titulo,
                'link': link,
                'descricao': descricao[:300].strip() if descricao else '',
                'data': pub_date.strftime('%d/%m/%Y') if pub_date else 'N/A',
                'relevante': relevante,
            })
    except Exception as e:
        print(f"Erro ao buscar feed [{nome}]: {e}")
    return itens


def build_email_body(resultados):
    today = date.today()
    total = sum(len(itens) for itens in resultados.values())
    total_relevantes = sum(1 for itens in resultados.values() for i in itens if i['relevante'])

    body = f"""<html><body>
<h2>&#9878; Monitor de Informativos STJ/STF &mdash; {today.strftime('%d/%m/%Y')}</h2>
<p>Publica&ccedil;&otilde;es dos &uacute;ltimos 7 dias: <b>{total}</b> | Potencialmente relevantes: <b style='color:#1e8449'>{total_relevantes}</b></p>
"""

    for fonte, itens in resultados.items():
        if not itens:
            continue
        relevantes = [i for i in itens if i['relevante']]
        outros = [i for i in itens if not i['relevante']]

        body += f"<h3>&#128196; {fonte} ({len(itens)} itens)</h3>"

        if relevantes:
            body += f"<h4 style='color:#1e8449'>&#10003; Possivelmente Relevantes ({len(relevantes)})</h4>"
            body += "<ul>"
            for item in relevantes:
                link_tag = f"<a href='{item['link']}' target='_blank'>{item['titulo']}</a>" if item['link'] else item['titulo']
                body += f"<li style='margin-bottom:8px'><b>[{item['data']}]</b> {link_tag}"
                if item['descricao']:
                    body += f"<br><small style='color:#555'>{item['descricao']}...</small>"
                body += "</li>"
            body += "</ul>"

        if outros:
            body += f"<details><summary style='cursor:pointer;color:#7f8c8d'>Outros ({len(outros)}) — expandir</summary><ul>"
            for item in outros:
                link_tag = f"<a href='{item['link']}' target='_blank'>{item['titulo']}</a>" if item['link'] else item['titulo']
                body += f"<li>[{item['data']}] {link_tag}</li>"
            body += "</ul></details>"

    if total == 0:
        body += "<p style='color:gray'>Nenhuma publica&ccedil;&atilde;o encontrada nos &uacute;ltimos 7 dias.</p>"

    body += f"""<hr>
<h4>&#128270; Palavras-chave monitoradas</h4>
<p style='color:#555;font-size:12px'>{', '.join(KEYWORDS_RELEVANTES)}</p>
<p><small>Monitor autom&aacute;tico semanal &mdash; Advocacia | CPC 927 (precedentes vinculantes) | Res. CNJ 455/2022</small></p>
</body></html>"""
    return body


def send_email(body, to_email, gmail_user, gmail_pass):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"[Advocacia] Informativos STJ/STF — {date.today().strftime('%d/%m/%Y')}"
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

    resultados = {}
    for nome, url in FEEDS.items():
        print(f"Buscando: {nome}...")
        itens = fetch_feed(nome, url, dias=7)
        resultados[nome] = itens
        print(f"  {len(itens)} itens encontrados")

    body = build_email_body(resultados)
    send_email(body, to_email, gmail_user, gmail_pass)
    total = sum(len(v) for v in resultados.values())
    print(f"Informativos enviados. Total: {total} publicacoes nos ultimos 7 dias.")


if __name__ == '__main__':
    main()
