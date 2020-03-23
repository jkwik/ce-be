from flask_mail import Mail, Message
from flask import render_template
from app import app
import os

def sendVerificationEmail(mail, to, first_name, last_name, verification_token):
    # Create the callback URL
    callback = ''
    if app.config["ENV"] == 'development':
        callback = os.getenv("DEV_ROOT_URL")
    else:
        callback = os.getenv("PROD_ROOT_URL")
    callback = callback + 'verifyUser?verification_token=' + verification_token

    try:
        msg = Message(
            "Welcome To Coach Easy!",
            sender="we.coach.easy@gmail.com",
            recipients=to
        )
        msg.body = 'Hello ' + first_name + ' ' + last_name + ',\n' + "Welcome to Coach Easy! We're excited to have you on board and to help you reach your fitness goals. Please click on the link below to verify your email and to make sure that we've got the right email address.\n" + "Please keep in mind that you won't be able to login until your coach has approved you. You will receive a follow up email when you've been approved.\n" + callback
        msg.html = render_template("welcome.html", name=first_name+' '+last_name, callback=callback)
        mail.send(msg)
        return None
    except Exception as e:
        return e
