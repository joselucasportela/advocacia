import csv
import smtplib
import os
from datetime import date, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


LIMITES = {
    'vip': 15,
    'comum': 30,
    'baixa': 60,
}


def load_clientes(filepath):
    with open(filepath, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def check_followup(clientes):
    today = date.today()
    precisam_contato = []
    sinais_churn = []

    for c in clientes:
        if c.get('status_caso', '').strip().lower() in ('encerrado', 'arquivado'):
            continue

        tipo = c.get('tipo_cliente', 'comum').strip().lower()
        limite = LIMITES.get(tipo, 30)

        ultimo_str = c.get('ultimo_contato', '').strip()
        if not ultimo_str:
            c['_dias_sem_contato'] = 999
            c['_limite'] = limite
            precisam_contato.append(c)
            continue

        try:
            ultimo = date.fromisoformat(ultimo_str)
        except ValueError:
            continue

        dias = (today - ultimo).days
        c['_dias_sem_contato'] = dias
        c['_limite'] = limite

        if dias >= limite:
            precisam_contato.append(c)

        # sinais de churn: sem contato por 2x o limite
        if dias >= limite * 2:
            sinais_churn.append(c)

    precisam_contato.sort(key=lambda x: x['_dias_sem_contato'], reverse=True)
    return precisam_contato, sinais_churn


def build_email_body(precisam_contato, sinais_churn):
    today = date.today()
    body = f"""<html><body>
<h2>&#128222; Monitor de Follow-up de Clientes &mdash; {today.strftime('%d/%m/%Y')}</h2>
<p>Clientes que precisam de contato: <b>{len(precisam_contato)}</b> | Sinais de churn: <b style='color:#c0392b'>{len(sinais_churn)}</b></p>
"""

    if sinais_churn:
        body += "<h3 style='color:#c0392b'>&#128308; Alerta de Churn &mdash; Contato Urgente</h3>"
        body += "<table border='1' cellpadding='6' cellspacing='0'>"
        body += "<tr style='background:#fadbd8'><th>Cliente</th><th>Tipo</th><th>Status Caso</th><th>Dias sem Contato</th><th>Limite</th><th>Ação Recomendada</th></tr>"
        for c in sinais_churn:
            body += (f"<tr><td><b>{c['cliente']}</b></td>"
                     f"<td>{c.get('tipo_cliente','')}</td>"
                     f"<td>{c.get('status_caso','')}</td>"
                     f"<td style='color:#c0392b'><b>{c['_dias_sem_contato']}d</b></td>"
                     f"<td>{c['_limite']}d</td>"
                     f"<td>Telefonar + e-mail de reativa&ccedil;&atilde;o</td></tr>")
        body += "</table><br>"

    nao_churn = [c for c in precisam_contato if c not in sinais_churn]
    if nao_churn:
        body += "<h3 style='color:#e67e22'>&#128203; Follow-up Pendente</h3>"
        body += "<table border='1' cellpadding='6' cellspacing='0'>"
        body += "<tr style='background:#fdebd0'><th>Cliente</th><th>Tipo</th><th>Status Caso</th><th>Último Contato</th><th>Dias</th><th>Ação</th></tr>"
        for c in nao_churn:
            acao = 'E-mail de atualização mensal' if c.get('tipo_cliente', '').lower() == 'vip' else 'E-mail de status trimestral'
            body += (f"<tr><td><b>{c['cliente']}</b></td>"
                     f"<td>{c.get('tipo_cliente','')}</td>"
                     f"<td>{c.get('status_caso','')}</td>"
                     f"<td>{c.get('ultimo_contato','Nunca')}</td>"
                     f"<td style='color:#e67e22'>{c['_dias_sem_contato']}d</td>"
                     f"<td>{acao}</td></tr>")
        body += "</table><br>"

    if not precisam_contato:
        body += "<p style='color:green'>&#10003; Todos os clientes est&atilde;o com contato em dia.</p>"

    body += """<hr>
<h4>Régua de Comunica&ccedil;&atilde;o (EAOAB art. 11)</h4>
<ul>
  <li><b>VIP:</b> E-mail mensal + reuni&atilde;o mensal + WhatsApp &lt; 4h &uacute;teis</li>
  <li><b>Comum:</b> E-mail trimestral + reuni&atilde;o trimestral</li>
  <li><b>Baixa:</b> E-mail semestral ou em marco do processo</li>
  <li><b>Gatilhos:</b> Decis&atilde;o → 48h | Senten&ccedil;a → 24h | Audi&ecirc;ncia → 48h da designa&ccedil;&atilde;o</li>
</ul>
<p><small>Monitor autom&aacute;tico &mdash; Advocacia | KPI meta: NPS &gt; 50 | Reten&ccedil;&atilde;o &gt; 85%</small></p></body></html>"""
    return body


def send_email(body, to_email, gmail_user, gmail_pass):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"[Advocacia] Monitor de Follow-up de Clientes — {date.today().strftime('%d/%m/%Y')}"
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

    clientes = load_clientes('data/clientes.csv')
    precisam_contato, sinais_churn = check_followup(clientes)
    body = build_email_body(precisam_contato, sinais_churn)
    send_email(body, to_email, gmail_user, gmail_pass)
    print(f"Follow-up enviado. Precisam contato: {len(precisam_contato)} | Churn: {len(sinais_churn)}")


if __name__ == '__main__':
    main()
