import os
BASE_DIR=os.path.abspath(os.path.dirname(__file__))
class Config:
 SECRET_KEY=os.environ.get('SECRET_KEY','smartgrocer-demo-secret')
 SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL','sqlite:///'+os.path.join(BASE_DIR,'instance','smartgrocer.db'))
 SQLALCHEMY_TRACK_MODIFICATIONS=False
 STORE_NAME='SmartGrocer'
 STORE_ADDRESS='12 Market Road, Chennai, Tamil Nadu'
 STORE_PHONE='+91 98765 43210'
 STORE_GSTIN='33ABCDE1234F1Z5'
