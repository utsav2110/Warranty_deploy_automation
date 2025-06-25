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
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background-color: #ff6b6b; padding: 20px; text-align: center; border-radius: 10px 10px 0 0;">
            <h1 style="color: white;">⚠️ Warranty Expiration Alert</h1>
            <p style="color: white;">The following items have warranties expiring tomorrow</p>
        </div>
        <div style="padding: 20px; background-color: white; border-radius: 0 0 10px 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
            <ul style="list-style-type: none; padding: 0;">
    """
    
    for item in expiring_items:
        email_body += f"""
            <li style="margin: 10px 0; padding: 10px; background-color: #fff3f3; border-radius: 5px; border-left: 4px solid #ff6b6b;">
                <strong style="color: #e74c3c;">{item[2]}</strong><br>
                Category: {item[3]}<br>
                Expires: {item[5]}
            </li>
        """
    
    email_body += """
            </ul>
            <div style="margin-top: 20px; padding: 15px; background-color: #f8f9fa; border-radius: 5px;">
                <p style="margin: 0; color: #2c3e50;">
                    Please take necessary action for the items listed above.
                </p>
            </div>
        </div>

        <div style="text-align: center; margin-top: 20px; color: #7f8c8d;">
            <p>This is an automated message, please do not reply to this email.</p>
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
