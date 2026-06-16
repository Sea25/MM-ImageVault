from django.shortcuts import render, redirect, get_object_or_404
from .models import ImageFile
import os

def home(request):
    if request.method == 'POST':
        images = request.FILES.getlist('images')

        for image in images:
            ImageFile.objects.create(image=image)
        return redirect('home')

    uploaded_images = ImageFile.objects.all().order_by('-uploaded_at')

    return render(request, 'imagevault/home.html', {'uploaded_images': uploaded_images})

def delete_image(request, id):
    image=get_object_or_404(ImageFile, id=id)
    if image.image and os.path.isfile(image.image.path):
        os.remove(image.image.path)
    image.delete()
    return redirect('home')