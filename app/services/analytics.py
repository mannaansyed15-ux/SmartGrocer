from datetime import datetime,timedelta
from sqlalchemy import func
from app.models import Bill, BillItem, Product, Category
from app import db
def restock_recommendations(limit=8):
 cutoff=datetime.utcnow()-timedelta(days=30); rows=[]
 for p in Product.query.all():
  sold=db.session.query(func.coalesce(func.sum(BillItem.quantity),0)).join(Bill).filter(BillItem.product_id==p.id,Bill.created_at>=cutoff).scalar() or 0
  daily=float(sold)/30; need=max(0,round(daily*14-float(p.stock_quantity),2))
  if need>0: rows.append({'product':p,'sold':float(sold),'need':need,'reason':'high recent demand' if daily>=1 else 'below safety stock'})
 return sorted(rows,key=lambda x:x['sold'],reverse=True)[:limit]
def sales_series(days=7):
 out=[]; today=datetime.utcnow().date()
 for i in range(days-1,-1,-1):
  d=today-timedelta(days=i); n=d+timedelta(days=1); total=db.session.query(func.coalesce(func.sum(Bill.grand_total),0)).filter(Bill.created_at>=d,Bill.created_at<n).scalar() or 0
  out.append({'date':d.isoformat(),'sales':float(total)})
 return out
