from flask import Flask, app 
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message

db = SQLAlchemy()
mail = Mail()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'kunci-rahasia-gudang'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gudang.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USE_SSL'] = False
    app.config['MAIL_USERNAME'] = 'ahmad240101034@gmail.com'
    app.config['MAIL_PASSWORD'] = 'fcbyanllzmwusggh'
    mail = Mail(app)

    db.init_app(app)
    mail.init_app(app)

    from app.routes import main
    app.register_blueprint(main)


    return app
