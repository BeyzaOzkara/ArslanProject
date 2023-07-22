import json
from django.http import HttpResponse
from django.shortcuts import render
from django.views import generic

# Create your views here.
def stockCard(request):
    print("true")
    return render(request, 'StokApp/stockCard.html')

""" class StokCardView(generic.TemplateView):
    template_name = 'StokApp/stockCard.html'

 """