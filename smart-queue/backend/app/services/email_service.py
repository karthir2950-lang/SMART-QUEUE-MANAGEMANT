import os
import re
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, Dict, Any, List
import requests

logger = logging.getLogger(__name__)

# Sandbox registry for capturing emails in test mode
SENT_EMAILS_REGISTRY: List[Dict[str, Any]] = []

def get_email_config() -> Dict[str, Any]:
    return {
        "provider": os.environ.get("EMAIL_PROVIDER", "resend").lower(),
        "from_email": os.environ.get("EMAIL_FROM", "QueueLess AI <reminders@queueless.app>"),
        "resend_api_key": os.environ.get("RESEND_API_KEY", ""),
        "sendgrid_api_key": os.environ.get("SENDGRID_API_KEY", ""),
        "smtp_host": os.environ.get("SMTP_HOST", ""),
        "smtp_port": int(os.environ.get("SMTP_PORT", "587")),
        "smtp_user": os.environ.get("SMTP_USER", ""),
        "smtp_pass": os.environ.get("SMTP_PASSWORD", ""),
        "smtp_tls": os.environ.get("SMTP_TLS", "true").lower() == "true",
        "frontend_url": os.environ.get("FRONTEND_URL", "https://karthir2950-lang.github.io/SMART-QUEUE-MANAGEMANT"),
        "is_test_mode": os.environ.get("EMAIL_TEST_MODE", "false").lower() == "true",
    }

def is_valid_email(email_str: Optional[str]) -> bool:
    if not email_str or not isinstance(email_str, str):
        return False
    email_regex = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    return bool(re.match(email_regex, email_str.strip()))

def render_reminder_email_html(
    user_name: str,
    service_name: str,
    organization_name: str,
    branch_name: str,
    date_str: str,
    time_str: str,
    remaining_label: str,
    token_number: Optional[str] = None,
    frontend_url: str = "https://karthir2950-lang.github.io/SMART-QUEUE-MANAGEMANT"
) -> str:
    token_badge = (
        f"""
        <div style="background-color: #f3f0ff; border: 1px solid #d8b4fe; border-radius: 8px; padding: 12px 16px; margin: 16px 0; display: inline-block;">
            <span style="font-size: 12px; font-weight: 600; color: #7c3aed; text-transform: uppercase; letter-spacing: 0.5px;">Queue Token Reference</span><br/>
            <span style="font-size: 24px; font-weight: 800; color: #581c87;">{token_number}</span>
        </div>
        """
        if token_number
        else """
        <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 16px; margin: 16px 0;">
            <span style="font-size: 13px; color: #64748b;">Queue Token: <strong>Generated upon check-in</strong></span>
        </div>
        """
    )

    action_url = f"{frontend_url.rstrip('/')}/#/user/appointments"

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QueueLess AI — Appointment Reminder</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1e293b;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #f8fafc; padding: 24px 0;">
        <tr>
            <td align="center">
                <table role="presentation" width="100%" style="max-width: 580px; background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05); border: 1px solid #e2e8f0;" cellspacing="0" cellpadding="0">
                    <!-- Header Banner -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); padding: 32px 32px 28px 32px; text-align: left;">
                            <div style="display: inline-block; background-color: rgba(255, 255, 255, 0.2); border-radius: 8px; padding: 6px 12px; margin-bottom: 12px;">
                                <span style="font-size: 12px; font-weight: 700; color: #ffffff; letter-spacing: 0.5px; text-transform: uppercase;">QueueLess AI Notification</span>
                            </div>
                            <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 700; line-height: 1.3;">Upcoming Appointment Reminder</h1>
                            <p style="margin: 8px 0 0 0; color: rgba(255, 255, 255, 0.9); font-size: 15px;">Your scheduled slot starts <strong>{remaining_label}</strong></p>
                        </td>
                    </tr>
                    
                    <!-- Content Body -->
                    <tr>
                        <td style="padding: 32px;">
                            <p style="margin: 0 0 16px 0; font-size: 16px; line-height: 1.6; color: #334155;">
                                Hello <strong>{user_name}</strong>,
                            </p>
                            <p style="margin: 0 0 20px 0; font-size: 15px; line-height: 1.6; color: #475569;">
                                This is a friendly automatic reminder that your upcoming appointment is scheduled for today. Please review the details below:
                            </p>
                            
                            <!-- Appointment Details Card -->
                            <table role="presentation" width="100%" style="background-color: #f8fafc; border-radius: 12px; border: 1px solid #e2e8f0; padding: 20px; margin-bottom: 24px;" cellspacing="0" cellpadding="0">
                                <tr>
                                    <td style="padding-bottom: 12px;">
                                        <span style="font-size: 12px; text-transform: uppercase; font-weight: 600; color: #64748b; letter-spacing: 0.5px;">Service</span><br/>
                                        <strong style="font-size: 16px; color: #0f172a;">{service_name}</strong>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding-bottom: 12px;">
                                        <span style="font-size: 12px; text-transform: uppercase; font-weight: 600; color: #64748b; letter-spacing: 0.5px;">Organization & Branch</span><br/>
                                        <strong style="font-size: 15px; color: #0f172a;">{organization_name}</strong> — <span style="color: #475569;">{branch_name}</span>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding-bottom: 12px;">
                                        <span style="font-size: 12px; text-transform: uppercase; font-weight: 600; color: #64748b; letter-spacing: 0.5px;">Date & Scheduled Time</span><br/>
                                        <strong style="font-size: 15px; color: #4f46e5;">📅 {date_str} at {time_str} IST</strong>
                                    </td>
                                </tr>
                                <tr>
                                    <td>
                                        {token_badge}
                                    </td>
                                </tr>
                            </table>

                            <!-- Action CTA Button -->
                            <div style="text-align: center; margin: 32px 0 24px 0;">
                                <a href="{action_url}" style="background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); color: #ffffff; text-decoration: none; font-size: 15px; font-weight: 600; padding: 14px 32px; border-radius: 10px; display: inline-block; box-shadow: 0 4px 6px -1px rgba(79, 70, 229, 0.25);">
                                    View Appointment & Queue Status &rarr;
                                </a>
                            </div>

                            <p style="margin: 0; font-size: 13px; line-height: 1.6; color: #64748b; text-align: center;">
                                Please arrive 10&ndash;15 minutes before your scheduled appointment time. You can view real-time queue position and AI estimated wait times on your dashboard.
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f1f5f9; padding: 20px 32px; text-align: center; border-top: 1px solid #e2e8f0;">
                            <p style="margin: 0; font-size: 12px; color: #64748b;">
                                &copy; 2026 QueueLess AI Platform. Universal Smart Queue & Appointment System.<br/>
                                If you need to reschedule or cancel, please access your appointments portal.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""

def render_reminder_email_text(
    user_name: str,
    service_name: str,
    organization_name: str,
    branch_name: str,
    date_str: str,
    time_str: str,
    remaining_label: str,
    token_number: Optional[str] = None,
    frontend_url: str = "https://karthir2950-lang.github.io/SMART-QUEUE-MANAGEMANT"
) -> str:
    token_line = f"Queue Token: {token_number}\n" if token_number else "Queue Token: Generated upon check-in\n"
    action_url = f"{frontend_url.rstrip('/')}/#/user/appointments"
    return (
        f"QueueLess AI — Upcoming Appointment Reminder ({remaining_label})\n\n"
        f"Hello {user_name},\n\n"
        f"This is an automated reminder that your scheduled appointment is starting {remaining_label}.\n\n"
        f"Appointment Details:\n"
        f"- Service: {service_name}\n"
        f"- Organization: {organization_name}\n"
        f"- Branch: {branch_name}\n"
        f"- Date: {date_str}\n"
        f"- Time: {time_str} IST\n"
        f"{token_line}\n"
        f"You can view live queue status and appointment details here:\n"
        f"{action_url}\n\n"
        f"Please arrive 10-15 minutes early.\n\n"
        f"— QueueLess AI Automated Reminder System"
    )

def send_appointment_reminder_email(
    recipient_email: str,
    user_name: str,
    service_name: str,
    organization_name: str,
    branch_name: str,
    date_str: str,
    time_str: str,
    remaining_label: str,
    token_number: Optional[str] = None,
    appointment_id: Optional[str] = None,
    reminder_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Sends an appointment reminder email using the configured provider.
    Fallback to test sandbox registry if running in test mode or if provider credentials are not yet set.
    """
    clean_email = (recipient_email or "").strip().lower()
    if not is_valid_email(clean_email):
        logger.warning(f"Invalid recipient email address: '{recipient_email}'")
        return {
            "success": False,
            "status": "FAILED",
            "error": f"Invalid recipient email format: '{recipient_email}'",
            "provider": "none"
        }

    config = get_email_config()
    frontend_url = config["frontend_url"]
    from_email = config["from_email"]

    subject = f"⏰ Reminder: Your appointment for {service_name} is {remaining_label} ({time_str} IST)"
    html_content = render_reminder_email_html(
        user_name=user_name,
        service_name=service_name,
        organization_name=organization_name,
        branch_name=branch_name,
        date_str=date_str,
        time_str=time_str,
        remaining_label=remaining_label,
        token_number=token_number,
        frontend_url=frontend_url
    )
    text_content = render_reminder_email_text(
        user_name=user_name,
        service_name=service_name,
        organization_name=organization_name,
        branch_name=branch_name,
        date_str=date_str,
        time_str=time_str,
        remaining_label=remaining_label,
        token_number=token_number,
        frontend_url=frontend_url
    )

    delivery_record = {
        "recipient": clean_email,
        "subject": subject,
        "appointment_id": str(appointment_id) if appointment_id else None,
        "reminder_type": reminder_type,
        "user_name": user_name,
        "service_name": service_name,
        "date_str": date_str,
        "time_str": time_str,
        "remaining_label": remaining_label,
        "token_number": token_number,
        "provider": config["provider"],
        "timestamp": None
    }

    # 1. Test Mode / Mock Sandbox Adapter (captures outbound emails deterministically)
    if config["is_test_mode"] or not (config["resend_api_key"] or config["sendgrid_api_key"] or config["smtp_host"]):
        from datetime import datetime, timezone
        delivery_record["timestamp"] = datetime.now(timezone.utc).isoformat()
        delivery_record["status"] = "SENT"
        SENT_EMAILS_REGISTRY.append(delivery_record)
        logger.info(f"[EmailService Sandbox] Captured reminder email to {clean_email} for appointment {appointment_id} ({reminder_type})")
        return {
            "success": True,
            "status": "SENT",
            "message_id": f"sandbox_{len(SENT_EMAILS_REGISTRY)}",
            "provider": "sandbox"
        }

    # 2. Resend API Adapter
    if config["provider"] == "resend" and config["resend_api_key"]:
        try:
            resp = requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {config['resend_api_key']}",
                    "Content-Type": "application/json"
                },
                json={
                    "from": from_email,
                    "to": [clean_email],
                    "subject": subject,
                    "html": html_content,
                    "text": text_content
                },
                timeout=10
            )
            if resp.status_code in (200, 201):
                res_data = resp.json()
                return {
                    "success": True,
                    "status": "SENT",
                    "message_id": res_data.get("id"),
                    "provider": "resend"
                }
            else:
                err_msg = f"Resend API error {resp.status_code}: {resp.text}"
                logger.error(err_msg)
                return {"success": False, "status": "FAILED", "error": err_msg, "provider": "resend"}
        except Exception as e:
            logger.error(f"Resend dispatch error: {e}")
            return {"success": False, "status": "FAILED", "error": str(e), "provider": "resend"}

    # 3. SendGrid API Adapter
    if config["provider"] == "sendgrid" and config["sendgrid_api_key"]:
        try:
            resp = requests.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={
                    "Authorization": f"Bearer {config['sendgrid_api_key']}",
                    "Content-Type": "application/json"
                },
                json={
                    "personalizations": [{"to": [{"email": clean_email}]}],
                    "from": {"email": from_email.split("<")[-1].replace(">", "").strip() if "<" in from_email else from_email},
                    "subject": subject,
                    "content": [
                        {"type": "text/plain", "value": text_content},
                        {"type": "text/html", "value": html_content}
                    ]
                },
                timeout=10
            )
            if resp.status_code in (200, 202):
                return {
                    "success": True,
                    "status": "SENT",
                    "message_id": resp.headers.get("X-Message-Id", "sg_ok"),
                    "provider": "sendgrid"
                }
            else:
                err_msg = f"SendGrid API error {resp.status_code}: {resp.text}"
                return {"success": False, "status": "FAILED", "error": err_msg, "provider": "sendgrid"}
        except Exception as e:
            return {"success": False, "status": "FAILED", "error": str(e), "provider": "sendgrid"}

    # 4. Standard SMTP Adapter
    if config["smtp_host"]:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = from_email
            msg["To"] = clean_email

            part1 = MIMEText(text_content, "plain")
            part2 = MIMEText(html_content, "html")
            msg.attach(part1)
            msg.attach(part2)

            with smtplib.SMTP(config["smtp_host"], config["smtp_port"], timeout=10) as server:
                if config["smtp_tls"]:
                    server.starttls()
                if config["smtp_user"] and config["smtp_pass"]:
                    server.login(config["smtp_user"], config["smtp_pass"])
                server.sendmail(from_email, [clean_email], msg.as_string())

            return {
                "success": True,
                "status": "SENT",
                "message_id": f"smtp_{appointment_id}",
                "provider": "smtp"
            }
        except Exception as e:
            return {"success": False, "status": "FAILED", "error": str(e), "provider": "smtp"}

    return {
        "success": False,
        "status": "FAILED",
        "error": "No email provider configured or credentials missing",
        "provider": "none"
    }
