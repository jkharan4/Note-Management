app_password = "saed ycvd tdfb wvlc"
import smtplib
from email.message import EmailMessage 
def send_mail(to, subject, body):
    server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    server.login("jkharan2@gmail.com",app_password)
    msg=EmailMessage()
    msg['From']='jkharan2@gmail.com'
    msg['To']=to
    msg['Subject']=subject
    msg.set_content(body)
    server.send_message(msg)
    server.close()