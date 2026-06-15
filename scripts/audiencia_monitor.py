import csv
import smtplib
import os
from datetime import date, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def load_audiencias(filepath):
    with open(filepath, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def check_audiencias(audiencias):
    today = date.today()
    alertas = {'1': [], '3': [], '7': []}

    for a in audiencias:
        try:
            data_aud = date.fromisoformat(a['data_audiencia'].strip())
        except ValueError:
            continue
        dias = (data_aud - today).days
        if dias == 1:
            alertas['1'].append(a)
        elif dias == 3:
            alertas['3'].append(a)
        elif dias == 7:
            alertas['7'].append(a)

    return alertas


def build_email_body(alertas):
    today = date.today()
    total = sum(len(v) for v in alertas.values())

    body = f"""<html><body>
<h2>&#9876; Monitor de Audi&ecirc;ncias &mdash; {today.strftime('%d/%m/%Y')}</h2>
<p>Audi&ecirc;ncias pr&oacute;ximas encontradas: <b>{total}</b></p>
"""

    if alertas['1']:
        body += "<h3 style='color:#c0392b'>&#9888; AMANH&Atilde; &mdash; Prepara&ccedil;&atilde;o imediata</h3>"
        body += "<table border='1' cellpadding='6' cellspacing='0'>"
        body += "<tr style='background:#fadbd8'><th>Processo</th><th>Cliente</th><th>Data</th><th>Hora</th><th>Vara</th><th>Tipo</th><th>Local</th></tr>"
        for a in alertas['1']:
            body += (f"<tr><td><b>{a['processo']}</b></td><td>{a['cliente']}</td>"
                     f"<td><b style='color:#c0392b'>{a['data_audiencia']}</b></td>"
                     f"<td>{a.get('hora','')}</td><td>{a['vara']}</td>"
                     f"<td>{a['tipo']}</td><td>{a.get('local','')}</td></tr>")
        body += "</table><br>"

    if alertas['3']:
        body += "<h3 style='color:#e67e22'>&#9889; EM 3 DIAS &mdash; Confirmar presen&ccedil;a e documentos</h3>"
        body += "<table border='1' cellpadding='6' cellspacing='0'>"
        body += "<tr style='background:#fdebd0'><th>Processo</th><th>Cliente</th><th>Data</th><th>Hora</th><th>Vara</th><th>Tipo</th><th>Local</th></tr>"
        for a in alertas['3']:
            body += (f"<tr><td><b>{a['processo']}</b></td><td>{a['cliente']}</td>"
                     f"<td>{a['data_audiencia']}</td><td>{a.get('hora','')}</td>"
                     f"<td>{a['vara']}</td><td>{a['tipo']}</td><td>{a.get('local','')}</td></tr>")
        body += "</table><br>"

    if alertas['7']:
        body += "<h3 style='color:#2980b9'>&#128197; EM 7 DIAS &mdash; Iniciar prepara&ccedil;&atilde;o</h3>"
        body += "<table border='1' cellpadding='6' cellspacing='0'>"
        body += "<tr style='background:#d6eaf8'><th>Processo</th><th>Cliente</th><th>Data</th><th>Hora</th><th>Vara</th><th>Tipo</th><th>Local</th></tr>"
        for a in alertas['7']:
            body += (f"<tr><td><b>{a['processo']}</b></td><td>{a['cliente']}</td>"
                     f"<td>{a['data_audiencia']}</td><td>{a.get('hora','')}</td>"
                     f"<td>{a['vara']}</td><td>{a['tipo']}</td><td>{a.get('local','')}</td></tr>")
        body += "</table><br>"

    if total == 0:
        body += "<p style='color:green'>&#10003; Nenhuma audi&ecirc;ncia nos pr&oacute;ximos 7 dias.</p>"

    body += """<hr>
<h4>Checklist D-1 (amanh&atilde;)</h4>
<ul>
  <li>Confirmar presen&ccedil;a de cliente / preposto / testemunhas</li>
  <li>Testar equipamento de videoconfer&ecirc;ncia</li>
  <li>Conferir endere&ccedil;o e tempo de deslocamento</li>
  <li>Imprimir carta de preposi&ccedil;&atilde;o (se PJ trabalhista)</li>
  <li>Cópia da procura&ccedil;&atilde;o + identidade do advogado</li>
</ul>
<p><small>Monitor autom&aacute;tico &mdash; Advocacia</small></p></body></html>"""
    return body


def send_email(body, to_email, gmail_user, gmail_pass):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"[Advocacia] Monitor de Audiências — {date.today().strftime('%d/%m/%Y')}"
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

    audiencias = load_audiencias('data/audiencias.csv')
    alertas = check_audiencias(audiencias)
    body = build_email_body(alertas)
    send_email(body, to_email, gmail_user, gmail_pass)

    total = sum(len(v) for v in alertas.values())
    print(f"Monitor de audiencias enviado. Alertas: {total}")


if __name__ == '__main__':
    main()
