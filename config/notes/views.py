from django.http import HttpResponse

def notes_list(request):
    return HttpResponse('Hello from Notes app.')
