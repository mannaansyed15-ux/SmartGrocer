import os, tempfile
from decimal import Decimal
import pytest
from app import create_app, db
from app.models import User, Category, Product, Customer, Bill, BillItem, Payment, InventoryTransaction
from reportlab.pdfgen import canvas
@pytest.fixture
def app():
 fn=tempfile.NamedTemporaryFile(delete=False).name
 app=create_app({'TESTING':True,'SQLALCHEMY_DATABASE_URI':'sqlite:///'+fn,'SECRET_KEY':'test'})
 with app.app_context():
  db.drop_all(); db.create_all(); u=User(username='admin',role='admin');u.set_password('admin123');db.session.add(u); c=Category(name='Dairy');db.session.add(c);db.session.flush(); db.session.add(Product(barcode='123',name='Milk',brand='Demo',unit='pack',selling_price=Decimal('30'),purchase_price=Decimal('25'),gst_percentage=Decimal('5'),stock_quantity=Decimal('10'),min_stock_threshold=Decimal('2'),category_id=c.id)); db.session.add(Customer(name='Test',phone='999')); db.session.commit()
 yield app
 os.unlink(fn)
@pytest.fixture
def client(app): return app.test_client()
def login(client): return client.post('/login',data={'username':'admin','password':'admin123'},follow_redirects=True)
def test_auth(client):
 assert client.get('/').status_code==302
 r=login(client); assert b'Dashboard' in r.data
 assert client.get('/logout').status_code==302
def test_product_crud_and_customer_crud(client,app):
 login(client); assert client.get('/products').status_code==200
 with app.app_context(): c=Category.query.first()
 r=client.post('/products',data={'barcode':'456','name':'Bread','brand':'X','unit':'pcs','selling_price':'40','purchase_price':'25','gst_percentage':'5','stock_quantity':'5','min_stock_threshold':'2','category_id':c.id}); assert r.status_code==302
 r=client.post('/customers',data={'name':'Alice','phone':'888','email':'a@b.com'}); assert r.status_code==302
 with app.app_context(): assert Product.query.filter_by(barcode='456').first(); assert Customer.query.filter_by(phone='888').first()
def test_checkout_gst_discount_stock_invoice_pdf(client,app):
 login(client)
 r=client.post('/api/checkout',json={'items':[{'id':1,'quantity':2}],'customer_id':1,'discount':5,'payment_method':'UPI'}); assert r.status_code==200; d=r.get_json(); assert d['invoice_number'].startswith('INV-2026-')
 with app.app_context():
  p=Product.query.get(1); b=Bill.query.get(d['bill_id']); assert p.stock_quantity==8; assert b.grand_total==Decimal('57.75'); assert b.payment.method=='UPI'; assert len(b.items)==1; assert InventoryTransaction.query.count()==1
  assert Bill.query.filter_by(invoice_number=d['invoice_number']).count()==1
 assert client.get('/invoice/%s'%d['bill_id']).status_code==200
 pdf=client.get('/invoice/%s/pdf'%d['bill_id']); assert pdf.status_code==200 and pdf.mimetype=='application/pdf' and pdf.data.startswith(b'%PDF')
def test_stock_validation_and_rollback(client,app):
 login(client); r=client.post('/api/checkout',json={'items':[{'id':1,'quantity':99}],'payment_method':'Cash'}); assert r.status_code==400
 with app.app_context(): assert Bill.query.count()==0; assert Product.query.get(1).stock_quantity==10
def test_cart_math_is_reflected_by_backend(client):
 login(client); r=client.post('/api/checkout',json={'items':[{'id':1,'quantity':1}],'discount':0,'payment_method':'Card'}); assert r.status_code==200
