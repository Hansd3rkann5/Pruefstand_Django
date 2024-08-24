from django.shortcuts import render
import mimetypes
from django.http import HttpResponse, FileResponse
from django.conf import settings
import os



# Create your views here.
def komp_pruefstand(request):
    return render(request, 'home.html')

def konfig(request):
    return render(request, 'konfig.html', )

def manu(request):
    return render(request, 'manu.html', )

def drop_konfig(request):
    return render(request, 'drop_konfig.html', )

def download_file(request, filenam):
    # fill these variables with real values
    file = os.path.join(settings.BASE_DIR, f'Test_Results/{filenam}')
    fileOpened = open(file, 'rb')
    return FileResponse(fileOpened, as_attachment=True, filename=filenam)



