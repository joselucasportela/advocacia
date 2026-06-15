import csv
import smtplib
import os
from datetime import date, timedelta
from decimal import Decimal
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def load_honorarios(filepath):
    with open(filepath, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def calcular_atualizado(valor_str, vencimento):
    today = date.today()
    try:
        valor = Decimal(valor_str.replace('R$', '').replace('.', '').replace(',', '.').strip())
    except Exception:
        return None, 0
    dias = (today - vencimento).days
    if dias <= 0:
        return float(valor), dias
    meses = Decimal(dias) / 30
    juros = valor * Decimal('0.01') * meses
    multa = valor * Decimal('0.10')
    total = valor + juros + multa
    return float(total), dias


def check_honorarios(honorarios):
    today = date.today()
    vencidos = []
    vence_em_5 = []

    for h in honorarios:
        if h.get('status', '').strip().lower() in ('pago', 'quitado'):
            continue
        try:
            venc = date.fromisoformat(h['vencimento'].strip())
        except ValueError:
            continue
        dias_ate = (venc - today).days
        dias_atraso = (today - venc).days

        if dias_atraso > 0:
            valor_atualizado, _ = calcular_atualizado(h.get('valor', '0'), venc)
            h['_atraso_dias'] = dias_atraso
            h['_valor_atualizado'] = valor_atualizado
            vencidos.append(h)
        elif 0 <= dias_ate <= 5:
            h['_dias_ate'] = dias_ate
            vence_em_5.append(h)

    vencidos.sort(key=lambda x: x['_atraso_dias'], reverse=True)
    vence_em_5.sort(key=lambda x: x['_dias_ate'])
    return vencidos, vence_em_5


def build_email_body(vencidos, vence_em_5):
    today = date.today()
    body = f"""<html><body>
<h2>&#128181; Monitor de Honor&aacute;rios &mdash; {today.strftime('%d/%m/%Y')}</h2>
<p>Parcelas vencidas: <b style='color:#c0392b'>{len(vencidos)}</b> | Vencem em at&eacute; 5 dias: <b style='color:#e67e22'>{len(vence_em_5)}</b></p>
"""

    if vencidos:
        body += "<h3 style='color:#c0392b'>&#128308; Honor&aacute;rios Vencidos</h3>"
        body += "<table border='1' cellpadding='6' cellspacing='0'>"
        body += "<tr style='background:#fadbd8'><th>Cliente</th><th>Descri&ccedil;&atilde;o</th><th>Parcela</th><th>Vencimento</th><th>Dias Atraso</th><th>Valor Original</th><th>Valor Atualizado</th></tr>"
        for h in vencidos:
            val_orig = h.get('valor', 'N/A')
            val_atual = f"R$ {h['_valor_atualizado']:.2f}" if h.get('_valor_atualizado') else 'N/A'
            body += (f"<tr><td><b>{h['cliente']}</b></td><td>{h.get('descricao','')}</td>"
                     f"<td>{h.get('parcela','')}</td><td>{h['vencimento']}</td>"
                     f"<td style='color:#c0392b'><b>{h['_atraso_dias']}d</b></td>"
                     f"<td>{val_orig}</td><td><b>{val_atual}</b></td></tr>")
        body += "</table>"
        body += "<p><small>Valor atualizado inclui juros 1%/m&ecirc;s (CC 406) + multa contratual 10%.</small></p><br>"

    if vence_em_5:
        body += "<h3 style='color:#e67e22'>&#9888; Vencem nos Pr&oacute;ximos 5 Dias</h3>"
        body += "<table border='1' cellpadding='6' cellspacing='0'>"
        body += "<tr style='background:#fdebd0'><th>Cliente</th><th>Descri&ccedil;&atilde;o</th><th>Parcela</th><th>Vencimento</th><th>Dias</th><th>Valor</th></tr>"
        for h in vence_em_5:
            cor = '#c0392b' if h['_dias_ate'] == 0 else '#e67e22' if h['_dias_ate'] <= 2 else '#000'
            body += (f"<tr><td><b>{h['cliente']}</b></td><td>{h.get('descricao','')}</td>"
                     f"<td>{h.get('parcela','')}</td><td>{h['vencimento']}</td>"
                     f"<td style='color:{cor}'><b>{h['_dias_ate']}d</b></td>"
                     f"<td>{h.get('valor','')}</td></tr>")
        body += "</table><br>"

    if not vencidos and not vence_em_5:
        body += "<p style='color:green'>&#10003; Nenhuma pendência financeira no momento.</p>"

    body += """<hr>
<h4>Régua de Cobran&ccedil;a (EAOAB art. 22)</h4>
<ul>
  <li>D+5: Lembrete amig&aacute;vel (WhatsApp/e-mail)</li>
  <li>D+15: Notifica&ccedil;&atilde;o interna formal</li>
  <li>D+30: Aviso de suspens&atilde;o de servi&ccedil;os</li>
  <li>D+60: Notifica&ccedil;&atilde;o extrajudicial via cart&oacute;rio</li>
  <li>D+90: A&ccedil;&atilde;o monitória (CPC 700) ou execu&ccedil;&atilde;o (CPC 784 III)</li>
</ul>
<p><small>Monitor autom&aacute;tico &mdash; Advocacia</small></p></body></html>"""
    return body


def send_email(body, to_email, gmail_user, gmail_pass):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"[Advocacia] Monitor de Honorários — {date.today().strftime('%d/%m/%Y')}"
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

    honorarios = load_honorarios('data/honorarios.csv')
    vencidos, vence_em_5 = check_honorarios(honorarios)
    body = build_email_body(vencidos, vence_em_5)
    send_email(body, to_email, gmail_user, gmail_pass)
    print(f"Monitor de honorarios enviado. Vencidos: {len(vencidos)} | Vence em 5d: {len(vence_em_5)}")


if __name__ == '__main__':
    main()
