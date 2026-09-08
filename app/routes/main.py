from functools import wraps
from datetime import datetime,timedelta,date
from decimal import Decimal,ROUND_HALF_UP
from flask import Blueprint,render_template,request,redirect,url_for,session,flash,jsonify,send_file,abort
from sqlalchemy import or_,func
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from io import BytesIO
from app import db
from app.models import *
from app.services.analytics import restock_recommendations,sales_series
bp=Blueprint('main',__name__)

def login_required(f):
 @wraps(f)
 def w(*a,**k):
  if 'user_id' not in session:return redirect(url_for('main.login'))
  return f(*a,**k)
 return w
def admin_required(f):
 @wraps(f)
 def w(*a,**k):
  if session.get('role')!='admin': abort(403)
  return f(*a,**k)
 return w
def money(v): return Decimal(str(v or 0)).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)
@bp.app_context_processor
def ctx(): return {'current_user':session.get('username'),'role':session.get('role')}
@bp.route('/login',methods=['GET','POST'])
def login():
 if request.method=='POST':
  u=User.query.filter_by(username=request.form.get('username','')).first()
  if u and u.check_password(request.form.get('password','')): session.update(user_id=u.id,username=u.username,role=u.role); return redirect(url_for('main.dashboard'))
  flash('Invalid credentials','error')
 return render_template('login.html')
@bp.route('/logout')
def logout(): session.clear(); return redirect(url_for('main.login'))
@bp.route('/')
@login_required
def dashboard():
 today=date.today(); tomorrow=today+timedelta(days=1)
 sales=db.session.query(func.coalesce(func.sum(Bill.grand_total),0)).filter(Bill.created_at>=today,Bill.created_at<tomorrow).scalar() or 0
 tx=Bill.query.filter(Bill.created_at>=today,Bill.created_at<tomorrow).count(); products=Product.query.count(); customers=Customer.query.count(); low=Product.query.filter(Product.stock_quantity<=Product.min_stock_threshold,Product.stock_quantity>0).count(); out=Product.query.filter(Product.stock_quantity<=0).count()
 recent=Bill.query.order_by(Bill.created_at.desc()).limit(8).all(); best=db.session.query(Product.name,func.sum(BillItem.quantity).label('q')).join(BillItem).group_by(Product.id).order_by(func.sum(BillItem.quantity).desc()).limit(5).all()
 return render_template('dashboard.html',sales=sales,tx=tx,products=products,customers=customers,low=low,out=out,recent=recent,best=best,series=sales_series())
@bp.route('/products',methods=['GET','POST'])
@login_required
def products():
 cats=Category.query.order_by(Category.name).all()
 if request.method=='POST':
  try:
   p=Product(barcode=request.form['barcode'].strip(),name=request.form['name'].strip(),brand=request.form.get('brand'),unit=request.form.get('unit') or 'pcs',selling_price=money(request.form['selling_price']),purchase_price=money(request.form['purchase_price']),gst_percentage=money(request.form.get('gst_percentage',0)),stock_quantity=Decimal(request.form.get('stock_quantity',0)),min_stock_threshold=Decimal(request.form.get('min_stock_threshold',5)),expiry_date=datetime.strptime(request.form['expiry_date'],'%Y-%m-%d').date() if request.form.get('expiry_date') else None,image_url=request.form.get('image_url'),category_id=int(request.form['category_id']))
   db.session.add(p); db.session.commit(); flash('Product added','success')
  except Exception as e: db.session.rollback(); flash('Could not add product: '+str(e),'error')
  return redirect(url_for('main.products'))
 q=request.args.get('q',''); cat=request.args.get('category',''); sort=request.args.get('sort','name')
 query=Product.query
 if q: query=query.filter(or_(Product.name.ilike('%'+q+'%'),Product.barcode.ilike('%'+q+'%'),Product.brand.ilike('%'+q+'%')))
 if cat: query=query.filter_by(category_id=int(cat))
 query=query.order_by(getattr(Product,sort if sort in ['name','selling_price','stock_quantity','expiry_date'] else 'name'))
 return render_template('products.html',products=query.all(),categories=cats)
@bp.route('/products/<int:id>/edit',methods=['POST'])
@login_required
def edit_product(id):
 p=Product.query.get_or_404(id)
 for f in ['barcode','name','brand','unit','image_url']: setattr(p,f,request.form.get(f,getattr(p,f)))
 for f in ['selling_price','purchase_price','gst_percentage','stock_quantity','min_stock_threshold']: setattr(p,f,Decimal(request.form.get(f,getattr(p,f))))
 p.category_id=int(request.form['category_id']); db.session.commit(); flash('Product updated','success'); return redirect(url_for('main.products'))
@bp.route('/products/<int:id>/delete',methods=['POST'])
@admin_required
def delete_product(id): db.session.delete(Product.query.get_or_404(id)); db.session.commit(); flash('Product deleted','success'); return redirect(url_for('main.products'))
@bp.route('/catalogue')
@login_required
def catalogue(): return render_template('catalogue.html',products=Product.query.all(),categories=Category.query.all())
@bp.route('/customers',methods=['GET','POST'])
@login_required
def customers():
 if request.method=='POST':
  c=Customer(name=request.form['name'],phone=request.form.get('phone'),email=request.form.get('email')); db.session.add(c); db.session.commit(); flash('Customer added','success'); return redirect(url_for('main.customers'))
 q=request.args.get('q',''); cs=Customer.query.filter(or_(Customer.name.ilike('%'+q+'%'),Customer.phone.ilike('%'+q+'%'))).all() if q else Customer.query.order_by(Customer.name).all(); return render_template('customers.html',customers=cs)
@bp.route('/customers/<int:id>/edit',methods=['POST'])
@login_required
def edit_customer(id):
 c=Customer.query.get_or_404(id); c.name=request.form['name']; c.phone=request.form.get('phone'); c.email=request.form.get('email'); db.session.commit(); flash('Customer updated','success'); return redirect(url_for('main.customers'))
@bp.route('/customers/<int:id>/delete',methods=['POST'])
@admin_required
def delete_customer(id): db.session.delete(Customer.query.get_or_404(id)); db.session.commit(); flash('Customer deleted','success'); return redirect(url_for('main.customers'))
@bp.route('/pos')
@login_required
def pos(): return render_template('pos.html',products=Product.query.filter(Product.stock_quantity>0).all(),customers=Customer.query.order_by(Customer.name).all())
@bp.route('/api/products')
@login_required
def api_products():
 q=request.args.get('q',''); ps=Product.query.filter(or_(Product.name.ilike('%'+q+'%'),Product.barcode==q)).filter(Product.stock_quantity>0).limit(20).all(); return jsonify([{'id':p.id,'name':p.name,'barcode':p.barcode,'price':float(p.selling_price),'gst':float(p.gst_percentage),'stock':float(p.stock_quantity),'unit':p.unit} for p in ps])
@bp.route('/api/checkout',methods=['POST'])
@login_required
def checkout():
 data=request.get_json() or {}; items=data.get('items',[]); discount=money(data.get('discount',0)); method=data.get('payment_method')
 if not items or method not in ['Cash','UPI','Card']: return jsonify(error='Invalid checkout data'),400
 try:
  subtotal=Decimal('0'); gst=Decimal('0'); built=[]
  for x in items:
   p=Product.query.get(int(x['id'])); qty=Decimal(str(x['quantity']))
   if not p or qty<=0 or qty>p.stock_quantity: raise ValueError(f'Insufficient stock for {p.name if p else "product"}')
   base=money(p.selling_price*qty); tax=money(base*p.gst_percentage/Decimal(100)); subtotal+=base; gst+=tax; built.append((p,qty,base,tax))
  if discount<0 or discount>subtotal: raise ValueError('Invalid discount')
  taxable=subtotal-discount; total_gst=money(sum((money(base*(p.gst_percentage/Decimal(100))) for p,q,base,tax in built),Decimal(0)))
  # GST is proportionalized after bill-level discount
  total_gst=money(sum((money((base/subtotal)*taxable*(p.gst_percentage/Decimal(100))) for p,q,base,tax in built),Decimal(0))) if subtotal else Decimal('0')
  grand=money(taxable+total_gst)
  b=Bill(invoice_number='PENDING',subtotal=subtotal,discount=discount,taxable_amount=taxable,total_gst=total_gst,grand_total=grand,cashier_id=session['user_id'],customer_id=data.get('customer_id') or None); db.session.add(b); db.session.flush(); b.invoice_number=f"INV-{datetime.utcnow().year}-{b.id:06d}"
  for p,q,base,tax in built:
   amount=money(base+(base/subtotal*taxable-base if subtotal else 0)+money(base/subtotal*taxable*(p.gst_percentage/Decimal(100)))) if False else money((base/subtotal)*taxable + (base/subtotal)*total_gst)
   db.session.add(BillItem(bill_id=b.id,product_id=p.id,quantity=q,unit_price=p.selling_price,gst_percentage=p.gst_percentage,discount=money((base/subtotal)*discount),amount=amount)); p.stock_quantity-=q; db.session.add(InventoryTransaction(product_id=p.id,quantity_change=-q,transaction_type='SALE',reference=b.invoice_number))
  db.session.add(Payment(bill_id=b.id,method=method,amount=grand))
  if b.customer: b.customer.total_purchases=money(b.customer.total_purchases+grand); b.customer.loyalty_points += int(grand//100)
  db.session.commit(); return jsonify(ok=True,bill_id=b.id,invoice_number=b.invoice_number)
 except Exception as e: db.session.rollback(); return jsonify(error=str(e)),400
@bp.route('/sales')
@login_required
def sales():
 q=request.args.get('q',''); query=Bill.query.join(Customer,isouter=True).join(Payment,isouter=True)
 if q: query=query.filter(or_(Bill.invoice_number.ilike('%'+q+'%'),Customer.name.ilike('%'+q+'%')))
 if request.args.get('payment'): query=query.filter(Payment.method==request.args['payment'])
 return render_template('sales.html',bills=query.order_by(Bill.created_at.desc()).all())
@bp.route('/invoice/<int:id>')
@login_required
def invoice(id): return render_template('invoice.html',bill=Bill.query.get_or_404(id))
@bp.route('/receipt/<int:id>')
@login_required
def receipt(id): return render_template('receipt.html',bill=Bill.query.get_or_404(id))
@bp.route('/invoice/<int:id>/pdf')
@login_required
def pdf(id):
 b=Bill.query.get_or_404(id); buf=BytesIO(); c=canvas.Canvas(buf,pagesize=A4); w,h=A4; y=h-45
 c.setFont('Helvetica-Bold',18); c.drawString(45,y,'SmartGrocer'); y-=22; c.setFont('Helvetica',9); c.drawString(45,y,'12 Market Road, Chennai | +91 98765 43210 | GSTIN 33ABCDE1234F1Z5'); y-=28
 c.setFont('Helvetica-Bold',11); c.drawString(45,y,f'Invoice {b.invoice_number}'); y-=16; c.setFont('Helvetica',9); c.drawString(45,y,f'{b.created_at:%d-%m-%Y %H:%M}  Cashier: {b.cashier.username}'); y-=20
 for text in ['Item','Qty','Rate','GST','Amount']:
  c.drawString([45,300,350,425,485][['Item','Qty','Rate','GST','Amount'].index(text)],y,text)
 y-=15
 for it in b.items:
  c.drawString(45,y,it.product.name[:38]); c.drawRightString(325,y,str(it.quantity)); c.drawRightString(400,y,f'₹{it.unit_price}'); c.drawRightString(460,y,f'{it.gst_percentage}%'); c.drawRightString(545,y,f'₹{it.amount}'); y-=14
 y-=10
 for label,val in [('Subtotal',b.subtotal),('Discount',b.discount),('GST',b.total_gst),('Grand Total',b.grand_total)]: c.drawRightString(460,y,label); c.drawRightString(545,y,f'₹{val}'); y-=15
 c.drawString(45,y,f'Payment: {b.payment.method}'); c.showPage(); c.save(); buf.seek(0); return send_file(buf,as_attachment=True,download_name=f'{b.invoice_number}.pdf',mimetype='application/pdf')
@bp.route('/inventory')
@login_required
def inventory():
 today=date.today(); soon=today+timedelta(days=7); ps=Product.query.order_by(Product.stock_quantity).all(); rec=restock_recommendations(); return render_template('inventory.html',products=ps,recs=rec,today=today,soon=soon)
@bp.route('/analytics')
@login_required
def analytics():
 top=db.session.query(Product.name,func.sum(BillItem.quantity).label('q')).join(BillItem).group_by(Product.id).order_by(func.sum(BillItem.quantity).desc()).limit(8).all(); cats=db.session.query(Category.name,func.sum(BillItem.quantity).label('q')).join(Product).join(BillItem).group_by(Category.id).all(); payments=db.session.query(Payment.method,func.count(Payment.id)).group_by(Payment.method).all(); return render_template('analytics.html',series=sales_series(30),top=top,cats=cats,payments=payments,recs=restock_recommendations())
