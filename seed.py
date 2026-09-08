from datetime import date,timedelta,datetime
from decimal import Decimal
from app import create_app,db
from app.models import *
app=create_app()
with app.app_context():
 db.drop_all(); db.create_all()
 admin=User(username='admin',role='admin'); admin.set_password('admin123'); cashier=User(username='cashier',role='cashier'); cashier.set_password('cashier123'); db.session.add_all([admin,cashier])
 names=['Fruits & Vegetables','Dairy','Beverages','Snacks','Rice & Grains','Personal Care','Household','Bakery']; cats={n:Category(name=n) for n in names}; db.session.add_all(cats.values()); db.session.flush()
 data=[('8901001','Banana Robusta','FreshFarm','kg',55,38,0,48,10,20),('8901002','Tomato','FreshFarm','kg',42,28,0,25,8,12),('8902001','Milk 500ml','Aavin','pack',32,26,5,12,15,5),('8902002','Curd 500g','Aavin','cup',40,31,5,8,10,4),('8903001','Orange Juice 1L','Tropicana','bottle',120,92,12,18,5,90),('8903002','Mineral Water 1L','Aquafina','bottle',20,12,18,70,20,180),('8904001','Potato Chips','Lay’s','pack',30,20,12,32,10,180),('8904002','Biscuits','Britannia','pack',25,17,12,50,15,240),('8905001','Basmati Rice 5kg','India Gate','bag',620,510,5,20,6,365),('8905002','Toor Dal 1kg','Tata Sampann','kg',165,132,5,6,8,300),('8906001','Bath Soap','Dove','bar',55,40,18,40,10,500),('8906002','Shampoo 180ml','Clinic Plus','bottle',95,72,18,18,6,500),('8907001','Dishwash Liquid 500ml','Vim','bottle',110,82,18,4,8,400),('8907002','Laundry Detergent 1kg','Surf Excel','pack',180,140,18,14,6,500),('8908001','Bread 400g','Modern','loaf',45,32,5,3,6,2),('8908002','Chocolate Muffin','FreshBake','pcs',35,22,5,16,5,3)]
 cat_order=names
 for i,(bar,n,b,u,sp,pp,g,st,m,days) in enumerate(data): db.session.add(Product(barcode=bar,name=n,brand=b,unit=u,selling_price=sp,purchase_price=pp,gst_percentage=g,stock_quantity=st,min_stock_threshold=m,expiry_date=date.today()+timedelta(days=days),category=cats[cat_order[i%8]],image_url='https://images.unsplash.com/photo-1542838132-92c53300491e?w=500'))
 for i in range(12): db.session.add(Customer(name=['Arun Kumar','Priya Sharma','Rahul Nair','Divya Iyer'][i%4]+f' {i+1}',phone=f'90000000{i:02d}',email=f'customer{i+1}@demo.local'))
 db.session.commit(); customers=Customer.query.all(); products=Product.query.all()
 # seed 18 sales over recent days for useful charts
 for i in range(18):
  p=products[i%len(products)]; qty=Decimal(str((i%3)+1)); base=p.selling_price*qty; gst=base*p.gst_percentage/100; b=Bill(invoice_number=f'INV-2026-{i+1:06d}',created_at=datetime.utcnow()-timedelta(days=i%7,hours=i%5),subtotal=base,discount=Decimal('0'),taxable_amount=base,total_gst=gst,grand_total=base+gst,cashier_id=cashier.id,customer_id=customers[i%len(customers)].id); db.session.add(b); db.session.flush(); db.session.add(BillItem(bill_id=b.id,product_id=p.id,quantity=qty,unit_price=p.selling_price,gst_percentage=p.gst_percentage,discount=0,amount=base+gst)); db.session.add(Payment(bill_id=b.id,method=['Cash','UPI','Card'][i%3],amount=base+gst)); db.session.add(InventoryTransaction(product_id=p.id,quantity_change=-qty,transaction_type='SEED_SALE',reference=b.invoice_number)); p.stock_quantity=max(Decimal('0'),p.stock_quantity-qty); b.customer.total_purchases += b.grand_total; b.customer.loyalty_points += int(b.grand_total//100)
 db.session.commit(); print('Seeded',len(products),'products',len(customers),'customers',Bill.query.count(),'bills')
