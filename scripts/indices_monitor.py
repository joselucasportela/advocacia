import csv
import smtplib
import os
import json
import requests
from datetime import date, datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# BCB OLINDA API — séries temporais públicas
# https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/
BCB_API = "https://servicodados.ibge.gov.br/api/v3/agregados"
BCB_SGS = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie}/dados/ultimos/{n}?formato=json"

SERIES = {
    'SELIC diária (% a.a.)': 432,
    'SELIC acumulada mês (% a.m.)': 4390,
    'IPCA mensal (%)': 433,
    'IPCA-E mensal (%)': 10764,
    'INPC mensal (%)': 188,
    'TR mensal (%)': 226,
    'IGP-M mensal (%)': 189,
}


def fetch_serie(serie_id, n=1):
    url = BCB_SGS.format(serie=serie_id, n=n)
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        dados = resp.json()
        if dados:
            return dados[-1]
    except Exception as e:
        print(f"Erro ao buscar serie {serie_id}: {e}")
    return None


def save_indices(indices, filepath):
    fieldnames = ['indicador', 'data', 'valor', 'atualizado_em']
    today_str = date.today().isoformat()
    rows = [{'indicador': nome, 'data': d['data'], 'valor': d['valor'], 'atualizado_em': today_str}
            for nome, d in indices.items() if d]
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_email_body(indices):
    today = date.today()
    body = f"""<html><body>
<h2>&#128200; Monitor de &Iacute;ndices Econ&ocirc;micos &mdash; {today.strftime('%d/%m/%Y')}</h2>
<p>Fonte: Banco Central do Brasil (BCB/OLINDA API)</p>
<table border='1' cellpadding='8' cellspacing='0' style='width:550px'>
<tr style='background:#2c3e50;color:white'><th>Indicador</th><th>Data de Refer&ecirc;ncia</th><th>Valor</th></tr>
"""

    for nome, dado in indices.items():
        if dado:
            valor = dado.get('valor', 'N/A')
            data_ref = dado.get('data', 'N/A')
            cor = '#d5e8d4' if nome.startswith('SELIC') else '#dae8fc' if 'IPCA' in nome else '#fff2cc'
            body += f"<tr style='background:{cor}'><td><b>{nome}</b></td><td>{data_ref}</td><td><b>{valor}%</b></td></tr>"
        else:
            body += f"<tr><td>{nome}</td><td colspan='2' style='color:gray'>Dados indispon&iacute;veis</td></tr>"

    body += "</table><br>"

    body += """<h4>&#128218; Aplica&ccedil;&atilde;o nos C&aacute;lculos Judiciais</h4>
<ul>
  <li><b>SELIC:</b> Repeti&ccedil;&atilde;o de ind&eacute;bito tribut&aacute;rio (Tema 962 STF) | Fazenda P&uacute;blica pós EC 113/2021</li>
  <li><b>IPCA-E:</b> Trabalhista pré 12/2021 (Tema 1.191 STF) | correc&atilde;o geral</li>
  <li><b>INPC:</b> Causas previdenci&aacute;rias (Lei 11.430/2006)</li>
  <li><b>TR:</b> Planos econ&ocirc;micos antigos | caderneta de poupan&ccedil;a</li>
  <li><b>IGP-M:</b> Loca&ccedil;&atilde;o (default contratual antigo)</li>
  <li><b>Juros mora:</b> 1% a.m. (CC 406) &mdash; n&atilde;o cumular com SELIC</li>
</ul>
<p><small>Atualiza&ccedil;&atilde;o autom&aacute;tica di&aacute;ria &mdash; Advocacia | Para c&aacute;lculos exatos, sempre conferir tabela oficial do tribunal.</small></p>
</body></html>"""
    return body


def send_email(body, to_email, gmail_user, gmail_pass):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"[Advocacia] Índices Econômicos — {date.today().strftime('%d/%m/%Y')}"
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

    print("Buscando indices no BCB...")
    indices = {}
    for nome, serie_id in SERIES.items():
        dado = fetch_serie(serie_id, n=1)
        indices[nome] = dado
        status = dado['valor'] if dado else 'ERRO'
        print(f"  {nome}: {status}")

    save_indices(indices, 'data/indices.csv')
    body = build_email_body(indices)
    send_email(body, to_email, gmail_user, gmail_pass)
    encontrados = sum(1 for d in indices.values() if d)
    print(f"Monitor de indices enviado. {encontrados}/{len(SERIES)} series obtidas.")


if __name__ == '__main__':
    main()
