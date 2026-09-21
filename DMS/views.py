import json
from django.shortcuts import render
from .models import EventData, TemporalData, RealTimeData
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Q
from ArslanTakipApp.models import Termik, KalipMs
from datetime import datetime

def event_deneme(request):
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
        
        print(f"Transferred: {oven_name} at {sample_time}")

    print("Data transfer complete!")

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

def event_data_view(request):
    return render(request, 'DMS/event_data.html')

def api_get_event_data(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    event_type = request.GET.get('event_type')
    machine_name = request.GET.get('machine_name')
    
    events = EventData.objects.using('dms').all()
    
    if start_date:
        events = events.filter(start_time__gte=start_date)
    if end_date:
        events = events.filter(start_time__lte=end_date)
    if event_type:
        events = events.filter(event_type__icontains=event_type)
    if machine_name:
        events = events.filter(machine_name__icontains=machine_name)
        
    data = []
    for e in events:
        static_data = e.static_data or {}
        data.append({
            'id': e.id,
            'event_type': e.event_type,
            'machine_name': e.machine_name,
            'start_time': e.start_time.strftime('%H:%M %d-%m-%y') if e.start_time else None,
            'end_time': e.end_time.strftime('%H:%M %d-%m-%y') if e.end_time else None,
            'kartNo': static_data.get('kartNo', ''),
            'operator': static_data.get('operator', ''),
            'profiles': static_data.get('profiles', ''),
            'BilletLot': static_data.get('BilletLot', ''),
            'DieNumber': static_data.get('DieNumber', ''),
            'StopCause': static_data.get('StopCause', ''),
            'Billet_Length_Pusher': static_data.get('Billet Length Pusher', ''),
        })
        
    return JsonResponse(data, safe=False)

def api_update_event_data(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            event_id = data.get('id')
            event = EventData.objects.using('dms').get(id=event_id)
            
            static_data = event.static_data or {}
            
            if 'kartNo' in data: static_data['kartNo'] = data['kartNo']
            if 'operator' in data: static_data['operator'] = data['operator']
            if 'profiles' in data: static_data['profiles'] = data['profiles']
            if 'BilletLot' in data: static_data['BilletLot'] = data['BilletLot']
            if 'DieNumber' in data: static_data['DieNumber'] = data['DieNumber']
            if 'StopCause' in data: static_data['StopCause'] = data['StopCause']
            if 'Billet_Length_Pusher' in data: static_data['Billet Length Pusher'] = data['Billet_Length_Pusher']
            
            event.static_data = static_data
            event.save(using='dms')
            
            return JsonResponse({'status': 'success'})
        except EventData.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Kayıt bulunamadı.'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Geçersiz istek.'}, status=400)

def api_get_kalip_nos(request):
    kalip_nos = list(KalipMs.objects.using('dies').values_list('KalipNo', flat=True).distinct())
    return JsonResponse(kalip_nos, safe=False)