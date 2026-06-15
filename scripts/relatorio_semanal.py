import csv
import smtplib
import os
from datetime import date
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def load_carteira(filepath):
    with open(filepath, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def build_relatorio(processos):
    today = date.today()
    ativos = [p for p in processos if p.get('status', '').strip().lower() == 'ativo']

    urgentes = []
    for p in ativos:
        prazo_str = p.get('proximo_prazo', '').strip()
        if not prazo_str:
            continue
        try:
            prazo = date.fromisoformat(prazo_str)
            dias = (prazo - today).days
            if 0 <= dias <= 7:
                urgentes.append((dias, p))
        except ValueError:
            pass
    urgentes.sort(key=lambda x: x[0])

    por_responsavel = {}
    for p in ativos:
        resp = p.get('responsavel', 'Sem responsável').strip()
        por_responsavel.setdefault(resp, []).append(p)

    inativos = [p for p in processos if p.get('status', '').strip().lower() != 'ativo']

    body = f"""<html><body>
<h2>&#128202; Relat&oacute;rio Semanal da Carteira &mdash; {today.strftime('%d/%m/%Y')}</h2>

<h3>Resumo Executivo</h3>
<table border='1' cellpadding='6' cellspacing='0' style='width:400px'>
  <tr style='background:#d5e8d4'><td><b>Processos ativos</b></td><td><b>{len(ativos)}</b></td></tr>
  <tr><td>Total na carteira</td><td>{len(processos)}</td></tr>
  <tr style='background:#fff2cc'><td>Com prazo nos pr&oacute;ximos 7 dias</td><td><b>{len(urgentes)}</b></td></tr>
  <tr><td>Inativos / arquivados</td><td>{len(inativos)}</td></tr>
</table><br>
"""

    if urgentes:
        body += "<h3 style='color:#c0392b'>&#9888; Prazos Urgentes (pr&oacute;ximos 7 dias)</h3>"
        body += "<table border='1' cellpadding='6' cellspacing='0'>"
        body += "<tr style='background:#fadbd8'><th>Processo</th><th>Cliente</th><th>Tribunal</th><th>Prazo</th><th>Dias</th><th>Respons&aacute;vel</th></tr>"
        for dias, p in urgentes:
            cor = '#c0392b' if dias <= 1 else '#e67e22' if dias <= 3 else '#000'
            body += (
                f"<tr><td>{p['processo']}</td><td>{p['cliente']}</td>"
                f"<td>{p['tribunal']}</td><td>{p['proximo_prazo']}</td>"
                f"<td style='color:{cor}'><b>{dias}d</b></td><td>{p['responsavel']}</td></tr>"
            )
        body += "</table><br>"

    body += "<h3>Processos por Respons&aacute;vel</h3>"
    for resp, procs in sorted(por_responsavel.items()):
        body += f"<h4>{resp} &mdash; {len(procs)} processo(s)</h4>"
        body += "<table border='1' cellpadding='5' cellspacing='0'>"
        body += "<tr style='background:#dae8fc'><th>Processo</th><th>Cliente</th><th>Tribunal</th><th>Status</th><th>Pr&oacute;ximo Prazo</th></tr>"
        for p in procs:
            body += (
                f"<tr><td>{p['processo']}</td><td>{p['cliente']}</td>"
                f"<td>{p['tribunal']}</td><td>{p['status']}</td>"
                f"<td>{p.get('proximo_prazo', '')}</td></tr>"
            )
        body += "</table><br>"

    if inativos:
        body += "<h3>Processos Inativos / Arquivados</h3>"
        body += "<table border='1' cellpadding='5' cellspacing='0'>"
        body += "<tr style='background:#f5f5f5'><th>Processo</th><th>Cliente</th><th>Tribunal</th><th>Status</th></tr>"
        for p in inativos:
            body += f"<tr><td>{p['processo']}</td><td>{p['cliente']}</td><td>{p['tribunal']}</td><td>{p['status']}</td></tr>"
        body += "</table><br>"

    body += "<hr><p><small>Relat&oacute;rio autom&aacute;tico semanal &mdash; Advocacia</small></p></body></html>"
    return body


def send_email(body, to_email, gmail_user, gmail_pass):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"[Advocacia] Relatório Semanal da Carteira — {date.today().strftime('%d/%m/%Y')}"
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

    processos = load_carteira('data/carteira.csv')
    body = build_relatorio(processos)
    send_email(body, to_email, gmail_user, gmail_pass)
    print(f"Relatorio semanal enviado. {len(processos)} processos processados.")


if __name__ == '__main__':
    main()
