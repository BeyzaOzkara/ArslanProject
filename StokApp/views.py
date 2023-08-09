import copy
import json
import time
from django.http import HttpResponse
from django.shortcuts import render
from django.views import generic
from ArslanTakipApp.models import Location

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

    rawData = [
        {'id': 1, 'locationName': '1.Fabrika', 'locationRelationID_id': None},
        {'id': 2, 'locationName': '2.Fabrika', 'locationRelationID_id': None},
        {'id': 48, 'locationName': 'YERİ BELLİ OLMAYANLAR', 'locationRelationID_id': None},
        {'id': 542, 'locationName': '1600 TON PRES', 'locationRelationID_id': 1},
        {'id': 543, 'locationName': '1200 TON PRES', 'locationRelationID_id': 1},
        {'id': 544, 'locationName': '1100 TON PRES', 'locationRelationID_id': 1},
        {'id': 545, 'locationName': 'KALIP HAZIRLAMA', 'locationRelationID_id': 1},
        {'id': 547, 'locationName': 'MEYDAN', 'locationRelationID_id': 545},
        {'id': 548, 'locationName': 'KALIP FIRINI 2', 'locationRelationID_id': 544},
        {'id': 549, 'locationName': 'KALIP FIRINI 1', 'locationRelationID_id': 544},
        {'id': 550, 'locationName': 'PRES', 'locationRelationID_id': 544},
        {'id': 551, 'locationName': 'PRES MEYDAN', 'locationRelationID_id': 544},
        {'id': 552, 'locationName': 'KALIP FIRINI 3', 'locationRelationID_id': 543},
        {'id': 553, 'locationName': 'KALIP FIRINI 2', 'locationRelationID_id': 543}
    ]

    num_duplicates = 1000
    duplicated_raw_data = duplicate_raw_data(rawData, num_duplicates)
    #print(duplicated_raw_data)
    time0 = time.time()
    #childData = list(Location.objects.values('id', 'locationName', 'locationRelationID_id').order_by('id'))
    print("Sorgu : " + str((time.time() - time0)) + " sn")
    
    time0 = time.time()
    opti = transform_data(duplicated_raw_data)
    #print(opti)

    data = json.dumps(opti)
    print("Format : " + str((time.time() - time0)) + " sn")
    
    context = {
        "data":data,
    } 
    return render(request, 'StokApp/stockCard.html', context)


"""  class StokCardView(generic.TemplateView):
    template_name = 'StokApp/stockCard.html' """

