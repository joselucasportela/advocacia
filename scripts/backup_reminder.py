import smtplib
import os
from datetime import date
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def build_email_body():
    today = date.today()
    mes_ano = today.strftime('%B/%Y').capitalize()
    body = f"""<html><body>
<h2>&#128190; Lembrete Mensal de Backup &mdash; {mes_ano}</h2>
<p>Este &eacute; o lembrete autom&aacute;tico mensal de backup do escrit&oacute;rio.<br>
Execute os itens abaixo e confirme a integridade dos dados.</p>

<h3>&#9989; Checklist Mensal de Backup</h3>
<table border='1' cellpadding='8' cellspacing='0' style='width:600px'>
<tr style='background:#2c3e50;color:white'><th>#</th><th>Tarefa</th><th>Feito?</th></tr>
<tr style='background:#d5e8d4'><td>1</td><td><b>Backup full semanal</b> — verificar se foi executado nos &uacute;ltimos 7 dias</td><td>[ ]</td></tr>
<tr><td>2</td><td><b>Teste de restore</b> — restaurar 1 arquivo aleat&oacute;rio e comparar hash (SHA-256)</td><td>[ ]</td></tr>
<tr style='background:#dae8fc'><td>3</td><td><b>Backup externo</b> — atualizar HD externo USB criptografado e guard&aacute;-lo fora do escrit&oacute;rio</td><td>[ ]</td></tr>
<tr><td>4</td><td><b>Cloud</b> — verificar quota e versionamento no Google Drive / OneDrive</td><td>[ ]</td></tr>
<tr style='background:#fff2cc'><td>5</td><td><b>Pastas de clientes encerrados</b> — verificar se foram arquivadas e com reten&ccedil;&atilde;o correta (5 anos — Provimento 188/2018 OAB)</td><td>[ ]</td></tr>
<tr><td>6</td><td><b>E-mails corporativos</b> — backup de e-mails dos &uacute;ltimos 30 dias</td><td>[ ]</td></tr>
<tr style='background:#d5e8d4'><td>7</td><td><b>Software de gest&atilde;o</b> — exportar backup do CRM jur&iacute;dico (Astrea / Projuris / ADVBOX)</td><td>[ ]</td></tr>
<tr><td>8</td><td><b>Logs de acesso</b> — verificar se est&atilde;o sendo retidos por 12 meses (Marco Civil art. 13)</td><td>[ ]</td></tr>
<tr style='background:#dae8fc'><td>9</td><td><b>Agenda e calend&aacute;rio</b> — exportar dados do Google Calendar / Outlook</td><td>[ ]</td></tr>
<tr><td>10</td><td><b>Documenta&ccedil;&atilde;o do teste</b> — registrar data, arquivo testado e resultado no log</td><td>[ ]</td></tr>
</table>

<h3>&#128274; Seguran&ccedil;a &mdash; Verificar Mensalmente</h3>
<ul>
  <li>2FA ativado em todas as contas (Google, e-mail, CRM, OneDrive)</li>
  <li>Nenhuma senha compartilhada por WhatsApp ou e-mail</li>
  <li>Acesso de ex-colaboradores revogado</li>
  <li>Antiv&iacute;rus / EDR atualizado em todos os dispositivos</li>
</ul>

<h3>&#128220; Bases Legais</h3>
<ul>
  <li><b>Provimento 188/2018 OAB:</b> 5 anos de reten&ccedil;&atilde;o pós encerramento da causa</li>
  <li><b>CC 205:</b> 30 anos para contratos (prescri&ccedil;&atilde;o m&aacute;xima)</li>
  <li><b>Marco Civil art. 13:</b> Logs de acesso → 12 meses</li>
  <li><b>LGPD art. 46-48:</b> Seguran&ccedil;a + comunica&ccedil;&atilde;o de incidente em 48h &agrave; ANPD</li>
  <li><b>CLT 11:</b> Folha de pagamento → 10 anos</li>
</ul>

<h3>&#128680; Em caso de incidente (ransomware, vazamento, perda)</h3>
<ol>
  <li><b>T+0h:</b> Desconectar m&aacute;quinas comprometidas + isolar rede</li>
  <li><b>T+2h:</b> Avaliar escopo — quais dados, quantos titulares</li>
  <li><b>T+12h:</b> Decidir sobre comunica&ccedil;&atilde;o &agrave; ANPD (portal anpd.gov.br)</li>
  <li><b>T+48h:</b> Comunicar ANPD e titulares afetados (LGPD art. 48)</li>
  <li><b>T+48h+:</b> Causa raiz + corre&ccedil;&atilde;o + atualizar pol&iacute;tica</li>
</ol>

<p><small>Lembrete autom&aacute;tico mensal (1&ordf; segunda-feira do m&ecirc;s) &mdash; Advocacia | Regra 3-2-1: 3 c&oacute;pias / 2 m&iacute;dias / 1 off-site</small></p>
</body></html>"""
    return body


def send_email(body, to_email, gmail_user, gmail_pass):
    today = date.today()
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"[Advocacia] Lembrete de Backup — {today.strftime('%B/%Y').capitalize()}"
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
    body = build_email_body()
    send_email(body, to_email, gmail_user, gmail_pass)
    print(f"Lembrete de backup enviado para {to_email}.")


if __name__ == '__main__':
    main()
