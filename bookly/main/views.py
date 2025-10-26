from django.shortcuts import render

def text(request):
    return render(request, 'main/shablon.html')

def first(request):
    return render(request, 'main/first.html')