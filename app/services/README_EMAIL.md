# Email Service Documentation

## Overview

The Email Service provides a centralized way to send emails throughout the CMS application. It supports HTML templates with Jinja2 and includes automatic fallback to plain text.

## Features

- ✉️ **Password Reset Emails**: Secure password reset links
- 🎉 **Welcome Emails**: Onboarding emails for new users
- 🔔 **Content Notifications**: Content approval/submission notifications
- 📧 **Generic Notifications**: Custom notification emails

## Configuration

Add these environment variables to your `.env` file:

```bash
# SMTP Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=noreply@cms-project.com
APP_URL=http://localhost:8000
```

### Gmail Setup

If using Gmail, you need to create an **App Password**:

1. Enable 2-Factor Authentication on your Google Account
2. Go to https://myaccount.google.com/apppasswords
3. Create a new App Password for "Mail"
4. Use this generated password as `SMTP_PASSWORD`

## Usage

### Import the Service

```python
from app.services.email_service import email_service
```

### Send Password Reset Email

```python
email_service.send_password_reset_email(
    to_email="user@example.com",
    username="johndoe",
    reset_token="abc123...xyz"
)
```

### Send Welcome Email

```python
email_service.send_welcome_email(
    to_email="newuser@example.com",
    username="janedoe"
)
```

### Send Content Approval Notification

```python
email_service.send_content_approval_notification(
    to_email="author@example.com",
    username="authorname",
    content_title="My Article",
    content_id=123,
    action="approved"  # or "submitted", "rejected"
)
```

### Send Generic Notification

```python
email_service.send_notification_email(
    to_email="user@example.com",
    username="username",
    subject="Important Update",
    message="Your account settings have been updated."
)
```

## Email Templates

Email templates are located in `templates/emails/`:

- `password_reset.html` - Password reset email template
- `welcome.html` - Welcome email template
- `content_notification.html` - Content approval notification template
- `notification.html` - Generic notification template

All templates support:
- Responsive design
- Professional styling
- Plain text fallback
- Brand customization

## Customizing Templates

Templates use Jinja2 syntax. Available variables:

### password_reset.html
- `username`: User's username
- `reset_link`: Full password reset URL
- `app_name`: Application name

### welcome.html
- `username`: User's username
- `login_url`: Login page URL
- `app_name`: Application name

### content_notification.html
- `username`: User's username
- `content_title`: Title of the content
- `message`: Notification message
- `content_url`: URL to view content
- `app_name`: Application name

### notification.html
- `username`: User's username
- `message`: Notification message
- `app_name`: Application name

## Testing

### Test Email Service Locally

Create a test script:

```python
from app.services.email_service import email_service

# Test email sending
result = email_service.send_welcome_email(
    to_email="test@example.com",
    username="testuser"
)

print(f"Email sent: {result}")
```

### Using Mailhog for Testing (Docker)

Add Mailhog to `docker-compose.yml`:

```yaml
mailhog:
  image: mailhog/mailhog
  ports:
    - "1025:1025"  # SMTP server
    - "8025:8025"  # Web UI
```

Update environment variables:

```bash
SMTP_HOST=mailhog
SMTP_PORT=1025
SMTP_USER=
SMTP_PASSWORD=
```

Access Mailhog UI at: http://localhost:8025

## Error Handling

The email service uses graceful error handling:

- Errors are logged but don't fail the main operation
- Registration/password reset will succeed even if email fails
- Useful for development when SMTP is not configured

## Production Considerations

### Security

1. **Use App Passwords**: Never use your main account password
2. **Enable TLS**: Port 587 with STARTTLS (default)
3. **Secure Credentials**: Use environment variables, never commit credentials
4. **Rate Limiting**: Consider rate limiting email sends

### Reliability

1. **Email Queue**: For high volume, use Celery + Redis queue
2. **Retry Logic**: Implement retry mechanism for failed sends
3. **Monitoring**: Track email delivery rates
4. **Backup SMTP**: Configure fallback SMTP server

### Compliance

1. **Unsubscribe Links**: Add unsubscribe option for marketing emails
2. **Privacy Policy**: Link to privacy policy in footer
3. **CAN-SPAM**: Comply with email regulations
4. **GDPR**: Handle user data appropriately

## Alternative SMTP Providers

### SendGrid

```bash
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=your-sendgrid-api-key
```

### AWS SES

```bash
SMTP_HOST=email-smtp.us-east-1.amazonaws.com
SMTP_PORT=587
SMTP_USER=your-ses-smtp-username
SMTP_PASSWORD=your-ses-smtp-password
```

### Mailgun

```bash
SMTP_HOST=smtp.mailgun.org
SMTP_PORT=587
SMTP_USER=your-mailgun-smtp-username
SMTP_PASSWORD=your-mailgun-smtp-password
```

## Troubleshooting

### Emails Not Sending

1. **Check SMTP credentials**: Verify username/password
2. **Check firewall**: Ensure port 587 is open
3. **Check logs**: Look for error messages
4. **Test connection**: Use telnet to test SMTP connection

```bash
telnet smtp.gmail.com 587
```

### Gmail "Less Secure Apps" Error

- Gmail no longer supports "less secure apps"
- You MUST use an App Password
- Enable 2FA first, then create App Password

### Emails Going to Spam

1. **SPF Records**: Configure SPF for your domain
2. **DKIM**: Enable DKIM signing
3. **DMARC**: Set up DMARC policy
4. **Reputation**: Use reputable SMTP provider
5. **Content**: Avoid spam trigger words

## Future Enhancements

- [ ] Email queue with Celery
- [ ] Email templates editor in admin panel
- [ ] Email analytics and tracking
- [ ] Unsubscribe management
- [ ] Email scheduling
- [ ] Attachment support
- [ ] Bulk email sending
- [ ] Email preview before sending

---

Last updated: 2026-01-10
