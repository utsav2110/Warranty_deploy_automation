import psycopg2
import os
from datetime import datetime,timedelta
from PIL import Image
from fpdf import FPDF
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import smtplib
import io

def get_user_email(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT email FROM users WHERE user_id = %s", (user_id,))
    email = cur.fetchone()
    cur.close()
    conn.close()
    return email[0] if email else None

def generate_expiring_warranty_pdf(expiring_items):
    pdf = FPDF()
    conn = get_conn()
    cur = conn.cursor()
    
    for item_name, expiry_date in expiring_items:
        cur.execute("""
            SELECT * FROM warranty_items 
            WHERE item_name = %s AND warranty_end_date = %s
        """, (item_name, expiry_date))
        warranty = cur.fetchone()
        if warranty:
            pdf.add_page()
            pdf.set_font('Arial', 'B', 16)
            pdf.cell(0, 10, f'Item: {warranty[2]}', ln=True)  
            pdf.set_font('Arial', '', 12)
            pdf.cell(0, 10, f'Category: {warranty[3]}', ln=True)  
            pdf.cell(0, 10, f'Purchase Date: {warranty[4]}', ln=True)  
            pdf.cell(0, 10, f'Warranty End Date: {warranty[5]}', ln=True)  
            pdf.cell(0, 10, f'Description: {warranty[7]}', ln=True)  

            if warranty[6]:  
                try:
                    image = Image.open(io.BytesIO(warranty[6]))
                
                    if image.mode != 'RGB':
                        image = image.convert('RGB')
                        
                    img_path = f"temp_{warranty[0]}.jpg"
                    image.save(img_path, 'JPEG', quality=85)
                    
                    try:
                        pdf.image(img_path, x=10, y=100, w=190)
                    finally:
                        if os.path.exists(img_path):
                            os.remove(img_path)
                except Exception as e:
                    pdf.cell(0, 10, f"Error including warranty image: {str(e)}", ln=True)

    cur.close()
    conn.close()
    return pdf.output(dest='S').encode('latin-1')  

def check_expiring_warranties(user_id=None):
    user_email = get_user_email(user_id)    
    sender = os.environ["SENDER_MAIL"]
    password = os.environ["SENDER_PASS"]
    conn = get_conn()
    cur = conn.cursor()
    tomorrow = datetime.now().date() + timedelta(days=1)
    
    cur.execute("""
        SELECT * FROM warranty_items 
        WHERE warranty_end_date = %s AND user_id = %s
    """, (tomorrow, user_id))
    
    expiring_items = cur.fetchall()
    cur.close()
    conn.close()
    
    if not expiring_items:
        return 
    
    email_body = f"""
    <div style="font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 600px; margin: 0 auto; background-color: #eef1f8; padding: 32px 16px;">
        <div style="background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 30px rgba(220,38,38,0.15);">
            <div style="background: linear-gradient(135deg, #dc2626, #f97316); background-color: #dc2626; padding: 36px 24px; text-align: center;">
                <div style="display: inline-block; width: 56px; height: 56px; line-height: 56px; background-color: rgba(255,255,255,0.15); border-radius: 50%; font-size: 26px; margin-bottom: 14px;">&#9888;&#65039;</div>
                <h1 style="color: #ffffff; font-size: 20px; margin: 0; font-weight: 600;">Warranty Expiration Alert</h1>
                <p style="color: rgba(255,255,255,0.85); font-size: 13px; margin: 4px 0 0;">The following items have warranties expiring tomorrow</p>
            </div>
            <div style="padding: 28px 24px; color: #1f2937;">
                <div style="text-align: center; background-color: #fef2f2; border-radius: 12px; padding: 16px; margin-bottom: 22px;">
                    <div style="font-size: 28px; font-weight: 700; color: #dc2626;">{len(expiring_items)}</div>
                    <div style="font-size: 12px; text-transform: uppercase; letter-spacing: 1px; color: #8b8fa3; font-weight: 600;">Expiring Tomorrow</div>
                </div>
    """

    for item in expiring_items:
        email_body += f"""
                <div style="padding: 14px 16px; background-color: #f9fafb; border-radius: 10px; margin-bottom: 10px; border-left: 4px solid #dc2626;">
                    <div style="font-size: 15px; font-weight: 600; color: #111827; margin-bottom: 6px;">&#128230; {item[2]}</div>
                    <div style="font-size: 13px; color: #6b7280;">
                        <span style="display: inline-block; background-color: #fee2e2; color: #b91c1c; padding: 2px 10px; border-radius: 12px; font-size: 11.5px; font-weight: 600; margin-right: 8px;">{item[3]}</span>
                        Expires: <strong>{item[5]}</strong>
                    </div>
                </div>
        """

    email_body += """
            </div>
            <div style="text-align: center; padding: 4px 24px 28px;">
                <p style="margin: 2px 0; font-size: 12px; color: #9ca3af;">This is an automated message, please do not reply to this email.</p>
            </div>
        </div>
    </div>
    """
    
    pdf_bytes = generate_expiring_warranty_pdf([(item[2], item[5]) for item in expiring_items])

    try:
        msg = MIMEMultipart("alternative")
        msg['Subject'] = 'Warranty Expiration Notice'
        msg['From'] = f"Warranty System <{sender}>"
        msg['To'] = user_email
        
        msg.attach(MIMEText(email_body, 'html'))
        
        pdf_attachment = MIMEApplication(pdf_bytes, _subtype='pdf')
        pdf_attachment.add_header('Content-Disposition', 'attachment', 
                                filename='expiring_warranties.pdf')
        msg.attach(pdf_attachment)
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
            smtp_server.login(sender, password)
            smtp_server.sendmail(sender, user_email, msg.as_string())
            
        print("✅ Successfully send the mail")
    except Exception as e:
        print(f"❌ Failed to send email: {str(e)}")


def get_conn():
    return psycopg2.connect(
        host=os.environ["SUPABASE_HOST"],
        dbname=os.environ["SUPABASE_DB"],
        user=os.environ["SUPABASE_USER"],
        password=os.environ["SUPABASE_PASS"],
        port=6543
    )

conn = get_conn()
cur = conn.cursor()
cur.execute("SELECT user_id FROM users WHERE role = 'user'")
user_ids = cur.fetchall()
cur.close()
conn.close()
for user_id in user_ids:
    check_expiring_warranties(user_id=user_id[0])

print("✅✅✅ All Done")
