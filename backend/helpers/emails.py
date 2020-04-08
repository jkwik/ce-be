from flask_mail import Mail, Message
from flask import render_template
from backend import app
import os

def sendVerificationEmail(mail, to, first_name, last_name, verification_token):
    # Create the callback URL
    callback = ''
    if app.config["ENV"] == 'development':
        callback = os.getenv("DEV_BACKEND_URL")
    else:
        callback = os.getenv("PROD_BACKEND_URL")
    callback = callback + 'verifyUser?email=' + to[0] + '&' + 'verification_token=' + verification_token

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

def sendApprovedEmail(mail, to, first_name, last_name):
    # Create the callback URL
    callback = ''
    if app.config["ENV"] == 'development':
        callback = os.getenv("PROD_FRONTEND_URL")
    else:
        callback = os.getenv("DEV_FRONTEND_URL")
    callback = callback + 'login'

    try:
        msg = Message(
            "You've Been Approved!",
            sender="we.coach.easy@gmail.com",
            recipients=to
        )
        msg.body = 'Hello ' + first_name + ' ' + last_name + ',\n' + "You've been successfully approved. You are now able to login to your account.\n" + callback
        msg.html = render_template("approved.html", name=first_name+' '+last_name, callback=callback)
        mail.send(msg)
        return None
    except Exception as e:
        return e

def forgotPasswordEmail(mail, to, first_name, last_name, reset_token):
    # Create the callback URL
    callback = ''
    if app.config["ENV"] == 'development':
        callback = os.getenv("PROD_FRONTEND_URL")
    else:
        callback = os.getenv("DEV_FRONTEND_URL")
    callback = callback + 'resetPassword?reset_token=' + reset_token

    try:
        msg = Message(
            "Forgot Password?",
            sender="we.coach.easy@gmail.com",
            recipients=to
        )
        msg.body = 'Hello ' + first_name + ' ' + last_name + ',\n' + "Reset password by clicking the button below.\n" + callback
        msg.html = render_template('forgotPassword.html', name=first_name+' '+last_name, callback=callback)
        mail.send(msg)
        return None
    except Exception as e:
        return e
