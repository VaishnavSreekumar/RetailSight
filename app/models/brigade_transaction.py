
from sqlalchemy import Column, DateTime, Float, Integer, String, Date, Time
from app.models.base import Base

class BrigadeTransaction(Base):
    __tablename__ = "brigade_transactions"

    order_id = Column(String, primary_key=True, index=True)
    coupon_code = Column(String, nullable=True)
    offer_name = Column(String, nullable=True)
    discount_code = Column(String, nullable=True)
    invoice_number = Column(String, index=True)
    invoice_type = Column(String, nullable=True)
    order_date = Column(Date)
    order_time = Column(Time)
    return_id = Column(String, nullable=True)
    store_id = Column(Integer)
    store_name = Column(String, nullable=True)
    city = Column(String, nullable=True)
    customer_name = Column(String, nullable=True)
    customer_number = Column(String, nullable=True)
    sku = Column(String, nullable=True)
    product_id = Column(String, nullable=True)
    ean = Column(String, nullable=True)
    product_name = Column(String)
    brand_name = Column(String, nullable=True)
    dep_name = Column(String, nullable=True)
    sub_category = Column(String, nullable=True)
    brand_type = Column(String, nullable=True)
    tax = Column(Float, nullable=True)
    hsn_code = Column(String, nullable=True)
    salesperson_id = Column(String, index=True)
    employee_code = Column(String, nullable=True)
    salesperson_name = Column(String, nullable=True)
    qty = Column(Integer)
    gmv = Column(Float) # Gross Merchandise Value
    nmv = Column(Float) # Net Merchandise Value
    coupon_amount = Column(Float, nullable=True)
    item_promotion = Column(Float, nullable=True)
    amt_without_gwp = Column(Float, nullable=True)
    total_amount = Column(Float)
    pb_eb_sale = Column(String, nullable=True)
    week_assigned = Column(String, nullable=True)
    tax_m = Column(Float, nullable=True)
    taxable_amt = Column(Float, nullable=True)
    tax_amt = Column(Float, nullable=True)
