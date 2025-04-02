import json
from django.shortcuts import render
from .models import EventData, TemporalData, RealTimeData
from django.utils import timezone
from ArslanTakipApp.models import Termik


def event_deneme(request):
    print("deneme")

    json_file_path = 'C:\\Users\\beyza.ozkara\\Desktop\\termik_data\\NodeRed.Termik.json'

    with open(json_file_path, 'r') as f:
        documents = json.load(f)

    for doc in documents:
        oven_name = doc.get('ovenName', '')
        sample_time = doc.get('sampleTime', {}).get('$numberLong', None)
        if sample_time:
            sample_time = int(sample_time) / 1000  # Convert to seconds for Django DateTimeField
            sample_time = timezone.make_aware(timezone.datetime.fromtimestamp(sample_time))  # Convert to timezone-aware datetime
        
        meta_data = {key: value for key, value in doc.items() if key not in ['ovenName', 'sampleTime']}
        
        real_time_data = RealTimeData(
            event_type='Aging',
            machine_name=oven_name,
            timestamp=sample_time,
            meta_data=meta_data
        )
        
        real_time_data.save()

def transfer_termik_to_realtime():
    termik_records = Termik.objects.all().exclude(OvenName='Y1600')

    for termik in termik_records:
        oven_name = termik.OvenName
        sample_time = termik.SampleTime

        sample_time = timezone.make_aware(sample_time)

        # meta_data = {}

        # if termik.Bolge1 is not None:
        #     meta_data['Bolge1'] = termik.Bolge1
        # if termik.OrtaBolge is not None:
        #     meta_data['OrtaBolge'] = termik.OrtaBolge
        # if termik.Bolge2 is not None:
        #     meta_data['Bolge2'] = termik.Bolge2
        # if termik.Bolge1TB is not None:
        #     meta_data['Bolge1TB'] = termik.Bolge1TB
        # if termik.Bolge2TB is not None:
        #     meta_data['Bolge2TB'] = termik.Bolge2TB
        # if termik.ProgramSet is not None:
        #     meta_data['ProgramSet'] = termik.ProgramSet
        # if termik.BatchNo is not None:
        #     meta_data['BatchNo'] = termik.BatchNo

        # real_time_data = RealTimeData(
        #     event_type='Aging',
        #     machine_name=oven_name,
        #     timestamp=sample_time,
        #     meta_data=meta_data
        # )

        # real_time_data.save()

        print(f"Transferred: {oven_name} at {sample_time}")

    print("Data transfer complete!")