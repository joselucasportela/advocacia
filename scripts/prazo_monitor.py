import csv
import smtplib
import os
from datetime import date
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def load_prazos(filepath):
    with open(filepath, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def check_prazos(prazos):
    today = date.today()
    criticos = {'1': [], '3': [], '7': []}

    for p in prazos:
        try:
            data_fatal = date.fromisoformat(p['data_fatal'].strip())
        except ValueError:
            continue
        dias = (data_fatal - today).days
        if dias == 1:
            criticos['1'].append(p)
        elif dias == 3:
            criticos['3'].append(p)
        elif dias == 7:
            criticos['7'].append(p)

    return criticos


def build_email_body(criticos):
    today = date.today()
    total = sum(len(v) for v in criticos.values())

    body = f"""<html><body>
<h2>&#128276; Monitor de Prazos &mdash; {today.strftime('%d/%m/%Y')}</h2>
<p>Prazos cr&iacute;ticos encontrados: <b>{total}</b></p>
"""

    if criticos['1']:
        body += "<h3 style='color:#c0392b'>&#9888; URGENTE &mdash; Vence AMANH&Atilde; (1 dia)</h3><table border='1' cellpadding='6' cellspacing='0'>"
        body += "<tr style='background:#fadbd8'><th>Processo</th><th>Cliente</th><th>Tipo do Ato</th><th>Data Fatal</th><th>Tribunal</th></tr>"
        for p in criticos['1']:
            body += f"<tr><td><b>{p['processo']}</b></td><td>{p['cliente']}</td><td>{p['tipo_ato']}</td><td><b style='color:#c0392b'>{p['data_fatal']}</b></td><td>{p['tribunal']}</td></tr>"
        body += "</table><br>"

    if criticos['3']:
        body += "<h3 style='color:#e67e22'>&#9889; ATEN&Ccedil;&Atilde;O &mdash; Vence em 3 dias</h3><table border='1' cellpadding='6' cellspacing='0'>"
        body += "<tr style='background:#fdebd0'><th>Processo</th><th>Cliente</th><th>Tipo do Ato</th><th>Data Fatal</th><th>Tribunal</th></tr>"
        for p in criticos['3']:
            body += f"<tr><td><b>{p['processo']}</b></td><td>{p['cliente']}</td><td>{p['tipo_ato']}</td><td><b style='color:#e67e22'>{p['data_fatal']}</b></td><td>{p['tribunal']}</td></tr>"
        body += "</table><br>"

    if criticos['7']:
        body += "<h3 style='color:#2980b9'>&#128197; ALERTA &mdash; Vence em 7 dias</h3><table border='1' cellpadding='6' cellspacing='0'>"
        body += "<tr style='background:#d6eaf8'><th>Processo</th><th>Cliente</th><th>Tipo do Ato</th><th>Data Fatal</th><th>Tribunal</th></tr>"
        for p in criticos['7']:
            body += f"<tr><td><b>{p['processo']}</b></td><td>{p['cliente']}</td><td>{p['tipo_ato']}</td><td>{p['data_fatal']}</td><td>{p['tribunal']}</td></tr>"
        body += "</table><br>"

    if total == 0:
        body += "<p style='color:green'>&#10003; Nenhum prazo cr&iacute;tico nos pr&oacute;ximos 7 dias.</p>"

    body += "<hr><p><small>Monitor autom&aacute;tico &mdash; Advocacia</small></p></body></html>"
    return body


def send_email(body, to_email, gmail_user, gmail_pass):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"[Advocacia] Monitor de Prazos — {date.today().strftime('%d/%m/%Y')}"
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

    prazos = load_prazos('data/prazos.csv')
    criticos = check_prazos(prazos)
    body = build_email_body(criticos)
    send_email(body, to_email, gmail_user, gmail_pass)

    total = sum(len(v) for v in criticos.values())
    print(f"Email enviado. Prazos criticos encontrados: {total}")


if __name__ == '__main__':
    main()
