from flask import Flask
from database import db
from models import Communication
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///instance/mobilize_crm.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    # Create index on user_id and date_sent
    print("Creating index on Communications table...")
    idx = db.Index('idx_comm_user_date', Communication.user_id, Communication.date_sent)
    idx.create(db.engine)
    print("Index created successfully!")
    
    # Create index on gmail_message_id
    print("Creating index on gmail_message_id...")
    idx2 = db.Index('idx_comm_gmail_id', Communication.gmail_message_id)
    idx2.create(db.engine)
    print("Index created successfully!") 