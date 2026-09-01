import os
import django
import sys
sys.path.append('c:\\Users\\beyza.ozkara\\ArslanDjango\\env\\ArslanProject')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ArslanProject.settings')
django.setup()
from ArslanTakipApp.models import KalipMs, User, Group, MusteriFirma, SiparisList
from django.db.models import F, Func, Count, Q

qs = KalipMs.objects.using('dies').annotate(trimmed_kalipno=Func(F('KalipNo'), function='REPLACE', template="%(function)s(%(expressions)s, ' ', '')")).exclude(Silindi=1).exclude(AktifPasif='Pasif')
duplicates = qs.values('trimmed_kalipno').annotate(c=Count('trimmed_kalipno')).filter(c__gt=1)
print('Duplicates count:', duplicates.count())
if duplicates.count() > 0:
    print('Sample duplicate:', duplicates.first())

# Let's check how many users are in the groups mentioned in the email send function.
rep_user = User.objects.all()
in_group_user = rep_user.filter(Q(groups__name="Yurt Ici Satis Bolumu") | Q(groups__name="Yurt Disi Satis Bolumu"))
print('Users in Yurt Ici or Yurt Disi Satis Bolumu:', in_group_user.count())

def test_mail_count():
    client_obj = MusteriFirma.objects.using('dies').filter(FirmaKodu='12345').values('MusteriTemsilcisi').first()
    # Actually wait, in test_report.py send_single_die_report:
    # reps = [rep.strip() for rep in client_obj['MusteriTemsilcisi'].split(',')]
    # Then it loops over reps.
    # What if a rep matches multiple users?
    # rep_user = User.objects.filter(last_name__istartswith=last_name, last_name__iendswith=last_name)
    # in_group_user = rep_user.filter(Q(groups__name="Yurt Ici Satis Bolumu") | Q(groups__name="Yurt Disi Satis Bolumu"))
    # if in_group_user.exists():
    #     rep_mail = in_group_user.values()[0]['email']
    #     # to_addresses.append(rep_mail)
    #     to_addresses.add(rep_mail)
    # That only adds one email, because to_addresses is a set.

    print("Checking email_mapping...")
test_mail_count()
