"""
Serviço de envio de e-mail assíncrono.
Usa SMTP com SSL (Gmail, Outlook ou qualquer provedor).
Variáveis necessárias no .env:
  SMTP_HOST     = smtp.gmail.com
  SMTP_PORT     = 587
  SMTP_USER     = seu-email@gmail.com
  SMTP_PASSWORD = sua-senha-de-app (não a senha normal — gere em myaccount.google.com)
  EMAIL_FROM    = "Financeiro App <seu-email@gmail.com>"
"""

import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=2)


def _send_sync(to_email: str, subject: str, html_body: str) -> None:
    """Envia e-mail de forma síncrona (executado em thread separada)."""
    host     = os.getenv("SMTP_HOST",     "smtp.gmail.com")
    port     = int(os.getenv("SMTP_PORT", "587"))
    user     = os.getenv("SMTP_USER",     "")
    password = os.getenv("SMTP_PASSWORD", "")
    from_raw = os.getenv("EMAIL_FROM",    f"Financeiro App <{user}>")

    if not user or not password:
        raise ValueError("SMTP_USER e SMTP_PASSWORD não configurados no .env")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = from_raw
    msg["To"]      = to_email
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(host, port, timeout=15) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(user, password)
        smtp.sendmail(user, [to_email], msg.as_string())

    logger.info(f"✅ E-mail enviado para {to_email}")


async def send_email(to_email: str, subject: str, html_body: str) -> None:
    """Wrapper assíncrono — executa o envio em thread pool para não bloquear o event loop."""
    import asyncio
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(_executor, _send_sync, to_email, subject, html_body)


def build_reset_email(nome: str, codigo: str) -> str:
    """Monta o HTML do e-mail de recuperação de senha."""
    return f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#F4F6F9;font-family:'Segoe UI',Arial,sans-serif">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center" style="padding:40px 16px">
      <table width="480" cellpadding="0" cellspacing="0"
             style="background:#fff;border-radius:20px;overflow:hidden;
                    box-shadow:0 4px 24px rgba(0,0,0,.08)">

        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#00897B,#00695C);
                     padding:32px 40px;text-align:center">
            <div style="font-size:36px;margin-bottom:8px">💰</div>
            <p style="color:#fff;font-size:20px;font-weight:800;margin:0">
              Recuperação de Senha
            </p>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="padding:36px 40px">
            <p style="color:#263238;font-size:15px;margin:0 0 16px">
              Olá, <strong>{nome}</strong>!
            </p>
            <p style="color:#607D8B;font-size:14px;line-height:1.6;margin:0 0 28px">
              Recebemos uma solicitação para redefinir a senha da sua conta no
              <strong>Financeiro App</strong>. Use o código abaixo no aplicativo:
            </p>

            <!-- Código -->
            <div style="background:#E0F2F1;border-radius:16px;
                        padding:24px;text-align:center;margin-bottom:28px">
              <p style="color:#00695C;font-size:11px;font-weight:700;
                         letter-spacing:2px;margin:0 0 8px">CÓDIGO DE VERIFICAÇÃO</p>
              <p style="color:#00897B;font-size:42px;font-weight:900;
                         letter-spacing:10px;margin:0;font-family:monospace">
                {codigo}
              </p>
              <p style="color:#607D8B;font-size:12px;margin:12px 0 0">
                ⏱ Válido por <strong>15 minutos</strong>
              </p>
            </div>

            <p style="color:#90A4AE;font-size:12px;line-height:1.6;margin:0">
              Se você não solicitou a redefinição de senha, ignore este e-mail.
              Sua senha permanece a mesma.
            </p>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="background:#F4F6F9;padding:20px 40px;text-align:center">
            <p style="color:#B0BEC5;font-size:11px;margin:0">
              © Financeiro App — Este é um e-mail automático, não responda.
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>
"""