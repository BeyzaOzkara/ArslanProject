import copy
import json
import time
from django.http import HttpResponse
from django.shortcuts import render
from django.views import generic
from ArslanTakipApp.models import Location, Hareket
from django.core import serializers
from django.core.serializers.json import DjangoJSONEncoder

def transform_data(raw_data):
    location_map = {}
    options = []

    # Create a map of location IDs to their corresponding dictionaries
    for item in raw_data:
        location_map[item['id']] = {'value': item['id'], 'name': item['locationName'], 'children': []}

    # Populate the children list for each location
    for item in raw_data:
        if item['locationRelationID_id'] is None:
            options.append(location_map[item['id']])
        else:
            parent = location_map[item['locationRelationID_id']]
            parent['children'].append(location_map[item['id']])

    return options

def transform_data2(raw_data):
    location_map = {}
    options = []

    """ # Create a map of location IDs to their corresponding dictionaries
    for item in raw_data:
        location_map[item['id']] = {'value': item['id'], 'name': item['kalipNo'], 'children': []}

    # Populate the children list for each location
    for item in raw_data:
            options.append(location_map[item['id']])
    return options """
    for item in raw_data:
        location_map[item['id']] = {'value': item['id'], 'name': item['locationName'], 'children': []}

    # Populate the children list for each location
    for item in raw_data:
        if item['locationRelationID_id'] is None:
            options.append(location_map[item['id']])
        else:
            parent = location_map[item['locationRelationID_id']]
            parent['children'].append(location_map[item['id']])

# rawDatas'ı rastgele çoğalt
def duplicate_raw_data(raw_data, num_duplicates):
    duplicated_data = []
    for _ in range(num_duplicates):
        new_data = copy.deepcopy(raw_data)
        id_offset = max(item['id'] for item in duplicated_data) + 1 if duplicated_data else 1
        for item in new_data:
            item['id'] = id_offset
            id_offset += 1
        duplicated_data.extend(new_data)
    return duplicated_data


# Create your views here.
def stockCard(request):
    print('stok kartı')

    #options = [{value, name, children[{}]}] şeklinde

    rawData = list(Location.objects.values('id', 'locationName', 'locationRelationID_id').order_by('id')) #list(Hareket.objects.values('id', 'kalipNo').order_by('id')[0:29])

    """ num_duplicates = 1000
    duplicated_raw_data = duplicate_raw_data(rawData, num_duplicates) """
    #print(duplicated_raw_data)
    #childData = list(Location.objects.values('id', 'locationName', 'locationRelationID_id').order_by('id'))
    time0 = time.time()
    
    #print("Sorgu : " + str((time.time() - time0)) + " sn")
    #print(rawData)

    time0 = time.time()
    opti = transform_data(rawData) #(duplicated_raw_data)
    #print(opti)

    data = json.dumps(opti, sort_keys=True, indent=1, cls=DjangoJSONEncoder)
    #print("Format : " + str((time.time() - time0)) + " sn")
    
    context = {
        "data":data,
    } 
    #print("Format2 : " + str((time.time() - time0)) + " sn")
    
    return render(request, 'StokApp/stockCard.html', context)

def stockCard_deneme(request):
    if request.method == 'GET':
           id = request.GET['id']
           print(id)
    time0 = time.time()
    #rawData = serializers.serialize("json", Hareket.objects.all().order_by('id')[0:29], fields=["kalipNo"])
    rawData = list(Location.objects.values('id', 'locationName', 'locationRelationID_id').order_by('id'))
    #rawData = list(Hareket.objects.values('id', 'kalipNo').filter(kalipVaris_id=id).order_by('id')[29:50])
    print("Sorgu : " + str((time.time() - time0)) + " sn")

    time0 = time.time()
    opti = transform_data(rawData) #(duplicated_raw_data)
    #print(opti)s

    data2 = json.dumps(opti, indent=1)
    print("Format : " + str((time.time() - time0)) + " sn")
    
    print(data2)
    return HttpResponse(data2, content_type="application/json")


"""  class StokCardView(generic.TemplateView):
    template_name = 'StokApp/stockCard.html' """

