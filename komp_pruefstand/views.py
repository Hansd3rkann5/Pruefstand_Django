from django.shortcuts import render



# Create your views here.
def komp_pruefstand(request):
    return render(request, 'home.html')

def konfig(request):
    return render(request, 'konfig.html', )

def manu(request):
    return render(request, 'manu.html', )

def drop_konfig(request):
    return render(request, 'drop_konfig.html', )




