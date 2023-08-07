import json
from django.http import HttpResponse
from django.shortcuts import render
from django.views import generic

# Create your views here.
def stockCard(request):
    print("true")
    childData= [{'id':1, 'locationName': '1.Fabrika', 'locationRelationID_id': None, 'isPhysical': False, 'children':[
                    {'id':4, 'locationName': '1.Fabrika cocuk', 'locationRelationID_id': 1, 'isPhysical': False, 'children':[
                    {'id':4, 'locationName': '1.Fabrika cocuk', 'locationRelationID_id': 1, 'isPhysical': False},
                    ]},
                ]},
                {'id':2, 'locationName': '2.Fabrika', 'locationRelationID_id': None, 'isPhysical': False},
                {'id':3, 'locationName': '3.Fabrika', 'locationRelationID_id': None, 'isPhysical': False},]
    data = json.dumps(childData)
    
    context = {
        "data":data,
    }
    return render(request, 'StokApp/stockCard.html', context)

""" class StokCardView(generic.TemplateView):
    template_name = 'StokApp/stockCard.html'

 """