import time
from bs4 import BeautifulSoup
from exchangelib import Credentials, Account, Message, DELEGATE, HTMLBody, Configuration, Folder
from .models import DiesLocation, LastProcessEmail, Hareket, Location
from django.contrib.auth.models import User
import logging

logger = logging.getLogger(__name__)

def send_email(username, password, to_address, subject, body, server):
    # Kimlik bilgileri ve hesap oluşturma
    credentials = Credentials(username, password)
    config = Configuration(server=server, credentials=credentials)
    account = Account(primary_smtp_address=username, config=config, autodiscover=False, access_type=DELEGATE)

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
                # print(f'Yeni e-posta - Gönderen: {email.sender.email_address}, Konu: {email.subject}')
                try:
                    movements = parse_die_movement(email.body)
                    save_movements(movements)
                except Exception as e:
                    logger.error(f"An error occurred while processing email: {e}")
        
        # Save the ID of the last processed email
        try:
            LastProcessEmail.objects.create(email_id=latest_email_id)
        except Exception as e:
            logger.error(f"An error occurred while saving the last processed email ID: {e}")

def parse_die_movement(email_body):
    try:
        soup = BeautifulSoup(email_body, 'html.parser')
        movements = []

        # Find all press codes with the specified color and background
        press_codes = soup.find_all('span', style=lambda value: value and 'color:red' in value and 'background:yellow' in value)
        
        for press_code in press_codes:
            die_numbers = []
            # Find the next siblings which are die numbers
            sibling = press_code.parent.find_next_sibling('p')
            while sibling:
                if sibling.name == 'p' and not sibling.find('span', style=lambda value: value and 'color:red' in value and 'background:yellow' in value):
                    text = sibling.get_text(strip=True)
                    if text:  # Check if the text is not empty
                        die_numbers.append(text)
                elif sibling.find('span', style=lambda value: value and 'color:red' in value and 'background:yellow' in value):
                    break
                sibling = sibling.find_next_sibling()
            
            if die_numbers:
                movements.append((press_code.get_text(strip=True), die_numbers))

        return movements
    except Exception as e:
        logger.error(f"An error occurred while parsing the email body: {e}")
        return []

def save_movements(movements):
    for press_code, die_numbers in movements:
        for die_number in die_numbers:
            try:
                last_location = DiesLocation.objects.get(KalipNo=die_number).kalipVaris
                Hareket.objects.create(
                    kalipNo=die_number,
                    kalipKonum=last_location,
                    kalipVaris=Location.objects.get(locationName__contains=press_code),
                    kimTarafindan=User.object.get(id=57),
                )
            except DiesLocation.DoesNotExist:
                logger.error(f"DiesLocation does not exist for KalipNo={die_number}")
            except Location.DoesNotExist:
                logger.error(f"Location does not exist for press_code={press_code}")
            except User.DoesNotExist:
                logger.error(f"User does not exist with id=57")
            except Exception as e:
                logger.error(f"An error occurred while saving movement: {e}")