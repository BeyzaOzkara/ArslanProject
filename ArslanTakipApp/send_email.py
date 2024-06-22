# -*- coding: utf-8 -*-

from .email_utils import send_email, read_emails, listen_for_emails

# Mail gönderme ve okuma ayarları
username = 'ai@arslanaluminyum.com'
password = 'Arslan123.'
server = 'webmail.arslanaluminyum.com'  # Sadece sunucu adresi, protokol yok
to_address = 'ufukizgi@arslanaluminyum.com'
subject = 'Deneme E-postası'
body = '<p>Merhaba,</p><p>Bu bir deneme e-postasıdır.</p>'

# Mail gönderme
#send_email(username, password, to_address, subject, body, server)

# Mail okuma
#read_emails(username, password, server, num_emails=10)

# Yeni e-postaları dinleme
listen_for_emails(username, password, server, check_interval=5)
