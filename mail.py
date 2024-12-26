import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr

EMAIL_ID = 'anandnagarjun5@gmail.com'
EMAIL_PASSWORD = 'teib fjhx ghfj zvzi'
EMAIL_SERVER_PORT = 587



# Function to initialize the email server
def initialize_email_server():
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo()
        server.starttls()  # Secure the connection
        server.ehlo()
        server.login(EMAIL_ID, EMAIL_PASSWORD)
        return server
    
    except Exception as e:
        print("Error initializing email server:", e)
        return None
    



# Function to send an email
def send_email(server, recipient_email: str, subject: str, html_content: str):
    try:
        # Create the email
        msg = MIMEMultipart()
        msg["From"] = formataddr(("SETN Support", EMAIL_ID))
        msg["To"] = recipient_email
        msg["Subject"] = subject

        # Attach the HTML content
        msg.attach(MIMEText(html_content, "html"))

        # Send the email
        server.sendmail(EMAIL_ID, recipient_email, msg.as_string())
        print("Email sent successfully to", recipient_email)
    except Exception as e:
        print("Error sending email:", e)



def send_reset_password_email(token: str, recipent_email: str):

    reset_url = f"http://localhost:8000/reset_password?token={token}"
    html_content = f"""
    <html>
    <body>
        <h2>Password Reset Request</h2>
        <p>We received a request to reset your password. Please click the button below to reset it:</p>
        <p>
            <a href="{reset_url}" style="
                display: inline-block;
                background-color: #007BFF;
                color: white;
                padding: 10px 20px;
                text-decoration: none;
                border-radius: 5px;
                font-size: 16px;
            ">
                Reset Password
            </a>
        </p>
        <p>If you did not request this, please ignore this email.</p>
        <p>Thank you,<br>SETN Support Team</p>
    </body>
    </html>
    """

    server = initialize_email_server()
    if server:
        print("Server connection established.")
        send_email(server, recipent_email, "Password Reset", html_content)
        server.quit()



