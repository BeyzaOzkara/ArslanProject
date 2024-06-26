import time
from exchangelib import Credentials, Account, Message, DELEGATE, HTMLBody, Configuration, Folder
from .models import LastProcessEmail, Hareket

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

    config = Configuration(service_endpoint=ews_url, credentials=credentials)
    # Connect to the Exchange server
    account = Account(
        primary_smtp_address=email,
        credentials=credentials,
        config=config,
        autodiscover=False,
        access_type=DELEGATE,
    )

    inbox = account.inbox
    try:
        latest_email_entry = LastProcessEmail.objects.latest('id')
        latest_email_id = latest_email_entry.email_id
    except LastProcessEmail.DoesNotExist:
        latest_email_id = None

    new_emails = []
    items = inbox.filter().order_by('-datetime_received')
    for item in items:
        if latest_email_id and item.id == latest_email_id:
            break
        new_emails.append(item)

    if new_emails:
        latest_email_id = new_emails[0].id
        for email in reversed(new_emails):
            print(f'Yeni e-posta - Gönderen: {email.sender.email_address}, Konu: {email.subject}')
            # parse_die_movement(email.body)
        
        # Save the ID of the last processed email
        LastProcessEmail.objects.create(email_id=latest_email_id)

