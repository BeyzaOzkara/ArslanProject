from collections import defaultdict
import re
import time
from bs4 import BeautifulSoup
from exchangelib import Credentials, Account, Message, DELEGATE, HTMLBody, Configuration, Folder
from .models import DiesLocation, LastProcessEmail, Hareket, Location, KalipMs
from django.contrib.auth.models import User
import logging
from django.db.models import Func, F, Value
from django.db.models.functions import Replace

logger = logging.getLogger(__name__)

def send_email(to_address, subject, body):
    email = 'yazilim@arslanaluminyum.com'
    password = 'rHE7Je'
    credentials = Credentials(email, password)
    ews_url ='https://webmail.arslanaluminyum.com/EWS/Exchange.asmx'
    # Kimlik bilgileri ve hesap oluşturma
    try:
        config = Configuration(service_endpoint=ews_url, credentials=credentials)
        # Connect to the Exchange server
        account = Account(
            primary_smtp_address=email,
            credentials=credentials,
            config=config,
            autodiscover=False,
            access_type=DELEGATE,
        )
    except Exception as e:
        logger.error(f"An error occurred while setting up the email account: {e}")
        
        return
    
    # E-posta mesajını oluşturma
    message = Message(
        account=account,
        folder=account.sent,
        subject=subject,
        body=HTMLBody(body),
        to_recipients=[to_address]
    )

    # E-postayı gönderme
    message.send()
    print("E-posta başarıyla gönderildi.")

def read_emails(username, password, server, folder='inbox', num_emails=10):
    # Kimlik bilgileri ve hesap oluşturma
    credentials = Credentials(username, password)
    config = Configuration(server=server, credentials=credentials)
    account = Account(primary_smtp_address=username, config=config, autodiscover=False, access_type=DELEGATE)

    # Gelen kutusundaki e-postaları alma
    inbox = account.inbox
    items = inbox.filter().order_by('-datetime_received')

    count = 0
    for item in items:
        if count >= num_emails:
            break
        print(f'Gönderen: {item.sender.email_address}')
        print(f'Konu: {item.subject}')
        print(f'Metin: {item.text_body}\n')
        count += 1

def listen_for_emails(username, password, server, check_interval=60):
    credentials = Credentials(username, password)
    config = Configuration(server=server, credentials=credentials)
    account = Account(primary_smtp_address=username, config=config, autodiscover=False, access_type=DELEGATE)

    inbox = account.inbox
    latest_email_id = None

    while True:
        items = inbox.filter().order_by('-datetime_received')
        if latest_email_id is None:
            latest_email_id = items[0].id if items else None

        new_emails = []
        for item in items:
            if item.id == latest_email_id:
                break
            new_emails.append(item)

        if new_emails:
            latest_email_id = new_emails[0].id
            for email in reversed(new_emails):
                print(f'Yeni e-posta - Gönderen: {email.sender.email_address}, Konu: {email.subject}')
                # Burada yeni e-posta için bildirim yapabilirsiniz (örneğin, bir log dosyasına yazabilir veya bir API çağrısı yapabilirsiniz)

        time.sleep(check_interval)  # Belirtilen süre kadar bekle (saniye cinsinden)

def check_new_emails():
    email = 'yazilim@arslanaluminyum.com'
    password = 'rHE7Je'
    credentials = Credentials(email, password)
    ews_url ='https://webmail.arslanaluminyum.com/EWS/Exchange.asmx'

    try:
        config = Configuration(service_endpoint=ews_url, credentials=credentials)
        # Connect to the Exchange server
        account = Account(
            primary_smtp_address=email,
            credentials=credentials,
            config=config,
            autodiscover=False,
            access_type=DELEGATE,
        )
    except Exception as e:
        logger.error(f"An error occurred while setting up the email account: {e}")
        return

    inbox = account.inbox
    try:
        latest_email_entry = LastProcessEmail.objects.latest('id')
        latest_email_id = latest_email_entry.email_id
    except LastProcessEmail.DoesNotExist:
        latest_email_id = None
    except Exception as e:
        logger.error(f"An error occurred while fetching the latest processed email: {e}")
        return

    new_emails = []
    try:
        items = inbox.filter().order_by('-datetime_received')
        for item in items:
            if latest_email_id and item.id == latest_email_id:
                break
            new_emails.append(item)
    except Exception as e:
        logger.error(f"An error occurred while fetching emails: {e}")
        return

    if new_emails:
        latest_email_id = new_emails[0].id
        for email in reversed(new_emails): #subject'e göre bakalım
            if email.subject == 'k':
                print(f'Yeni e-posta - Gönderen: {email.sender.email_address}, Konu: {email.subject}')
                # print(email.body)
                movements = parse_die_movement(email.body)
                print(f'movements: {movements}')
                wrong_numbers, saved_numbers = save_move(movements)
                print(f'wrong_numbers: {wrong_numbers}, saved_numbers: {saved_numbers}')
                # maili atan kişiye başarılı ve başarısız olan kalıp numaralarını mail at.
                send_results(email.sender.email_address, wrong_numbers, saved_numbers)
        
        # Save the ID of the last processed email
        try:
            LastProcessEmail.objects.create(email_id=latest_email_id)
        except Exception as e:
            logger.error(f"An error occurred while saving the last processed email ID: {e}")

def parse_die_movement(email_body):
    try:
        soup = BeautifulSoup(email_body, 'html.parser')
        movements = []
        # Find the table in the HTML content
        table = soup.find('table', class_='MsoNormalTable')
        
        if table:
            rows = table.find_all('tr')
            
            # Skip the header row
            for row in rows[1:]:
                cols = row.find_all('td')
                
                # Extract press code and kalip numbers
                if len(cols) >= 2:
                    press_code = cols[0].get_text(strip=True)
                    kalip_numbers = cols[1].get_text(strip=True)
                    kalip_numbers = re.sub(r'\s+', ' ', kalip_numbers).strip()
                    movements.append({'press_code': press_code, 'kalip_numbers': kalip_numbers})

        return movements
    except Exception as e:
        logger.error(f"An error occurred while parsing the email body: {e}")
        return []

presler = {
    '1600-1':542, '1200':543, '1100-1':544, '4000':570, 
    '2750':571, '1600-2':572, 'Y1100':573, '4500':1105
}

def save_move(movements):
    wrong_numbers = defaultdict(list)
    saved_numbers = defaultdict(list)
    try:
        kalipms_queryset = KalipMs.objects.using('dies').annotate(
                        kalipNo_spaces=Replace(
                            Replace(
                                F('KalipNo'),
                                Value(' '),
                                Value('')
                            ),
                            Value('\t'),  # In case there are tab characters
                            Value('')
                        )
                    )
        dies_location_queryset = DiesLocation.objects.annotate(
                                kalipNo_no_spaces=Replace(
                                    Replace(
                                        F('kalipNo'),
                                        Value(' '),
                                        Value('')
                                    ),
                                    Value('\t'),  # In case there are tab characters
                                    Value('')
                                )
                            )
        for movement in movements:
            press_code = movement['press_code']
            kalip_numbers = movement['kalip_numbers']
            
            # Check if kalip numbers is not empty
            if kalip_numbers:
                kalip_list = kalip_numbers.split(',')
                for kalip_no in kalip_list:
                    original_kalip_no = kalip_no.strip()
                    kalip_no = original_kalip_no
                    try:
                        kalip_ms = kalipms_queryset.filter(KalipNo=kalip_no).first()
                        
                        if not kalip_ms:
                            kalip_ms = kalipms_queryset.filter(KalipNo=kalip_no + " R").first()
                            if kalip_ms:
                                kalip_no = kalip_no + " R"

                        if not kalip_ms:
                            wrong_numbers[press_code].append(original_kalip_no)
                            continue

                        # Check last location in DiesLocation
                        dies_location = dies_location_queryset.filter(kalipNo=kalip_no).first()
                        
                        if dies_location:
                            if dies_location.kalipVaris_id == presler[press_code]:
                                saved_numbers[press_code].append(kalip_no)
                                continue
                            last_location = dies_location.kalipVaris
                        else:
                            last_location = None

                        Hareket.objects.create(
                            kalipNo=kalip_no,
                            kalipKonum=last_location,
                            kalipVaris_id=presler[press_code],
                            kimTarafindan_id=57,
                        )

                        saved_numbers[press_code].append(kalip_no)
                    except Exception as e:
                        logger.error(f"Error processing kalip_no {kalip_no}: {e}")
    except Exception as e:
        logger.error(f"Error in save_move function: {e}")

    formatted_wrong_numbers = [
        {'press_code': press_code, 'kalip_numbers': ', '.join(kalip_nos)}
        for press_code, kalip_nos in wrong_numbers.items()
    ]
    formatted_saved_numbers = [
        {'press_code': press_code, 'kalip_numbers': ', '.join(kalip_nos)}
        for press_code, kalip_nos in saved_numbers.items()
    ]

    return formatted_wrong_numbers, formatted_saved_numbers

def send_results(to_email, wrong_numbers, saved_numbers):
    subject = "Kalıp Hareketleri"

    # Create the HTML email content
    html = f"""
    <html>
    <head>
    <style>
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        table, th, td {{
            border: 1px solid black;
        }}
        th, td {{
            padding: 10px;
            text-align: left;
        }}
        th {{
            background-color: #f2f2f2;
        }}
    </style>
    </head>
    <body>
        <h2>Başarılı Gönderilenler</h2>
        <table>
            <tr>
                <th>Pres</th>
                <th>Kalıp Numaraları</th>
            </tr>"""

    for item in saved_numbers:
        html += f"""
            <tr>
                <td>{item['press_code']}</td>
                <td>{item['kalip_numbers']}</td>
            </tr>"""

    html += """
        </table>
        <h2>Başarısız Numaralar</h2>
        <table>
            <tr>
                <th>Pres</th>
                <th>Kalıp Numaraları</th>
            </tr>"""

    for item in wrong_numbers:
        html += f"""
            <tr>
                <td>{item['press_code']}</td>
                <td>{item['kalip_numbers']}</td>
            </tr>"""

    html += """
        </table>
    </body>
    </html>"""

    send_email(to_email, subject, html)