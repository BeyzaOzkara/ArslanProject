import json
from django.http import HttpResponse
from django.shortcuts import render
from django.views import generic

# Create your views here.
def stockCard(request):
    print("true")
    childData= [{'locationName': '1.Fabrika', 'locationRelationID_id': None, 'isPhysical': False},
                {'locationName': '1.Fabrika', 'locationRelationID_id': None, 'isPhysical': False},
                {'locationName': '1.Fabrika', 'locationRelationID_id': None, 'isPhysical': False},]
    data = json.dumps(childData)
    return render(request, 'StokApp/stockCard.html', {'loc_json':data})

""" class StokCardView(generic.TemplateView):
    template_name = 'StokApp/stockCard.html'

 """