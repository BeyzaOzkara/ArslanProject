from collections import defaultdict
import re
import os
import time
from bs4 import BeautifulSoup
from exchangelib import Credentials, Account, Message, DELEGATE, HTMLBody, Configuration, Folder, FileAttachment
from .models import DiesLocation, LastProcessEmail, Hareket, Location, KalipMs
from django.contrib.auth.models import User
import logging
from django.db.models import Func, F, Value
from django.db.models.functions import Replace

logger = logging.getLogger(__name__)

def send_email(to_addresses, cc_recipients, subject, body, attachments=None):
    logger.info('MAIL SEND START to=%s subject=%r', to_addresses, subject)
    email = os.environ.get('AI_EMAIL_USER', 'ai@arslanaluminyum.com')
    password = os.environ.get('AI_EMAIL_PASSWORD', '')
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
        logger.exception('MAIL SEND CONNECT ERROR account=%s', email)
        
        return False
    
    # E-posta mesajını oluşturma
    message = Message(
        account=account,
        folder=account.sent,
        subject=subject,
        body=HTMLBody(body),
        to_recipients=to_addresses,
        cc_recipients=cc_recipients
    )

    # E-postayı gönderme
    try:
        for name, content, content_type in attachments or []:
            message.attach(FileAttachment(name=name, content=content, content_type=content_type))
            logger.info('MAIL ATTACHMENT name=%s bytes=%s', name, len(content))
        message.send()
    except Exception:
        logger.exception('MAIL SEND ERROR to=%s subject=%r', to_addresses, subject)
        raise
    logger.info('MAIL SEND OK Exchange gonderimi kabul etti to=%s subject=%r', to_addresses, subject)
    print("E-posta başarıyla gönderildi.")
    return True

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
    from .sevkiyat_report import is_sevkiyat_completed, send_sevkiyat_report, normalize_text

    email = os.environ.get('AI_EMAIL_USER', 'ai@arslanaluminyum.com')
    password = os.environ.get('AI_EMAIL_PASSWORD', '')
    credentials = Credentials(email, password)
    ews_url ='https://webmail.arslanaluminyum.com/EWS/Exchange.asmx'

    logger.info('MAIL CHECK START mailbox=%s password_configured=%s', email, bool(password))
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
        logger.exception('MAIL CHECK CONNECT ERROR mailbox=%s', email)
        return

    inbox = account.inbox
    try:
        latest_email_entry = LastProcessEmail.objects.latest('id')
        latest_email_id = latest_email_entry.email_id
    except LastProcessEmail.DoesNotExist:
        latest_email_id = None
    except Exception as e:
        logger.exception('MAIL CHECK CHECKPOINT READ ERROR')
        return

    logger.info('MAIL CHECK CHECKPOINT present=%s', bool(latest_email_id))
    new_emails = []
    try:
        # Tüm alanları istemek her mail için GetItem çağrıları ve gövde indirmesi
        # oluşturur. Önce yalnızca hafif FindItem alanlarıyla işaretçiyi bul.
        items = inbox.filter().only('subject', 'datetime_received').order_by('-datetime_received')
        found_checkpoint = False
        logger.info('MAIL CHECK SCAN START mode=headers_only')
        for scanned, item in enumerate(items, 1):
            if latest_email_id and item.id == latest_email_id:
                found_checkpoint = True
                break
            new_emails.append(item)
            if scanned == 1 or scanned % 100 == 0:
                logger.info('MAIL CHECK SCAN scanned=%s received=%s', scanned, item.datetime_received)
        if latest_email_id and not found_checkpoint:
            logger.warning('MAIL CHECK CHECKPOINT NOT FOUND; mevcut mailler atlanmadan islenecek')
    except Exception as e:
        logger.exception('MAIL CHECK INBOX ERROR')
        return

    logger.info('MAIL CHECK NEW count=%s', len(new_emails))
    if new_emails:
        for email in reversed(new_emails): #subject'e göre bakalım
            if normalize_text(email.subject) == 'sevkiyat' or email.subject == 'GÖNDERİLEN KALIPLAR':
                logger.info('MAIL CHECK FETCH DETAIL id=%s subject=%r', email.id, email.subject)
                email = inbox.get(id=email.id)
            logger.info('MAIL CHECK ITEM id=%s sender=%s subject=%r', email.id,
                        getattr(getattr(email, 'sender', None), 'email_address', ''), email.subject)
            if is_sevkiyat_completed(email):
                # Hata durumunda işaretçi ilerlemez; sonraki kontrolde tekrar denenir.
                try:
                    send_sevkiyat_report(
                        shipment_datetime=email.datetime_sent or email.datetime_received,
                        sender_email=email.sender.email_address,
                    )
                except Exception:
                    logger.exception('SEVKIYAT REPORT FAILED email_id=%s; mail tekrar denenecek', email.id)
                    raise
            if email.subject == 'GÖNDERİLEN KALIPLAR':
                print(f'Yeni e-posta - Gönderen: {email.sender.email_address}, Konu: {email.subject}')
                movements = parse_die_movement(email.body)
                print(f'movements: {movements}')
                wrong_numbers, saved_numbers = save_move(movements)
                print(f'wrong_numbers: {wrong_numbers}, saved_numbers: {saved_numbers}')
                # maili atan kişiye başarılı ve başarısız olan kalıp numaralarını mail at.
                send_results([email.sender.email_address], wrong_numbers, saved_numbers)
        
            # Her başarılı mailden sonra kaydet; sonraki mailin hatası önceki
            # raporların bütün partiyle birlikte yeniden gönderilmesine yol açmasın.
            try:
                LastProcessEmail.objects.create(email_id=email.id)
            except Exception:
                logger.exception('MAIL CHECK CHECKPOINT WRITE ERROR email_id=%s', email.id)
                raise
            logger.info('MAIL CHECK ITEM DONE id=%s', email.id)
    logger.info('MAIL CHECK DONE')

def parse_die_movement(email_body):
    try:
        soup = BeautifulSoup(email_body, 'html.parser')
        movements = []
        # Find the table in the HTML content
        table = soup.find('table', class_='MsoNormalTable')
        
        if table:
            rows = table.find_all('tr')
            header_row = rows[0]
            headers = [cell.get_text(strip=True) for cell in header_row.find_all('td')]

            # Initialize a dictionary to store the numbers for each header
            movement_dict = {header: [] for header in headers}

            # Process data rows
            for row in rows[1:]:
                cols = row.find_all('td')
                for index, col in enumerate(cols):
                    kalip_numbers = col.get_text(separator=',', strip=True)
                    if kalip_numbers:
                        movement_dict[headers[index]].append(kalip_numbers)

            # Convert movement_dict to the required format
            for header, numbers in movement_dict.items():
                if numbers:
                    movements.append({'press_code': header, 'kalip_numbers': ', '.join(numbers)})

        return movements
    except Exception as e:
        logger.error(f"An error occurred while parsing the email body: {e}")
        return []

presler = {
    '1600-1':542, '1200':543, '1100':544, '4000':570, 
    '2750':571, '1600-2':572, 'Y1100':573, '4500':1105,
    '1.Fabrika Kalıp Hazırlama': 547, '2.Fabrika Kalıp Hazırlama': 766,
    'Kalıp Arşivi': 575, 'KalıpArşivi': 575, 'Kalıp Depo':1132, 'Kalıphane':1133
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

    # send_email(to_addresses=to_email, cc_recipients="", subject= subject, body= html)
