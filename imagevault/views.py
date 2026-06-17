from django.shortcuts import render, redirect, get_object_or_404
from django.core.files.base import ContentFile
from PIL import Image
from pillow_heif import register_heif_opener
from .models import ConvertedImage
import os
from io import BytesIO


register_heif_opener()


def home(request):
    if request.method == 'POST':
        uploaded_file = request.FILES.get('image')
        output_format = request.POST.get('output_format')

        if uploaded_file and output_format:
            converted = ConvertedImage.objects.create(
                original_image=uploaded_file,
                output_format=output_format
            )

            image = Image.open(converted.original_image.path)

            if output_format in ['JPG', 'JPEG']:
                image = image.convert('RGB')
                file_extension = 'jpg'
                pillow_format = 'JPEG'
            else:
                file_extension = output_format.lower()
                pillow_format = output_format

            buffer = BytesIO()

            if pillow_format == 'PNG':
                image.save(buffer, format=pillow_format)
            elif pillow_format == 'WEBP':
                image.save(buffer, format=pillow_format, quality=100)
            else:
                image.save(buffer, format=pillow_format, quality=100)

            new_filename = os.path.splitext(uploaded_file.name)[0] + '.' + file_extension

            converted.converted_image.save(
                new_filename,
                ContentFile(buffer.getvalue()),
                save=True
            )

            return redirect('home')

    images = ConvertedImage.objects.all().order_by('-uploaded_at')

    return render(request, 'imagevault/home.html', {
        'images': images
    })


def delete_image(request, id):
    image = get_object_or_404(ConvertedImage, id=id)

    if image.original_image and os.path.isfile(image.original_image.path):
        os.remove(image.original_image.path)

    if image.converted_image and os.path.isfile(image.converted_image.path):
        os.remove(image.converted_image.path)

    image.delete()
    return redirect('home')