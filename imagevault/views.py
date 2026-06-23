from django.shortcuts import render, redirect, get_object_or_404
from django.core.files.base import ContentFile
from django.http import JsonResponse
from PIL import Image, ImageSequence
from pillow_heif import register_heif_opener
from .models import ConvertedImage
from io import BytesIO
import os, base64, zipfile

register_heif_opener()

PILLOW_FORMAT_MAP = {
    'JPG': ('JPEG', 'jpg'), 'JPEG': ('JPEG', 'jpg'),
    'PNG': ('PNG', 'png'), 'WEBP': ('WEBP', 'webp'),
    'BMP': ('BMP', 'bmp'), 'TIFF': ('TIFF', 'tiff'),
    'GIF': ('GIF', 'gif'), 'ICO': ('ICO', 'ico'),
}

ICO_SIZES = {
    '16': (16, 16), '32': (32, 32), '48': (48, 48),
    '64': (64, 64), '128': (128, 128), '256': (256, 256),
}

def home(request):
    if request.method == 'POST':
        uploaded_file = request.FILES.get('image')
        output_format = request.POST.get('output_format', '').upper()
        ico_size = request.POST.get('ico_size', 'original')

        if uploaded_file and output_format:
            converted = ConvertedImage.objects.create(
                original_image=uploaded_file,
                output_format=output_format
            )

            image = Image.open(converted.original_image.path)
            pillow_format, file_extension = PILLOW_FORMAT_MAP.get(output_format, ('PNG', 'png'))

            is_animated = hasattr(image, 'n_frames') and image.n_frames > 1

            if is_animated:
                # Load and copy all frames immediately to avoid lazy file pointer/seeking issues
                frames = [f.copy() for f in ImageSequence.Iterator(image)]
                image.close()

                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    num_frames = len(frames)
                    digits = len(str(num_frames))

                    for i, frame in enumerate(frames):
                        frame_image = frame.convert('RGBA')

                        # Mode conversions
                        if pillow_format == 'JPEG':
                            frame_image = frame_image.convert('RGB')
                        elif pillow_format == 'BMP':
                            frame_image = frame_image.convert('RGB')
                        elif pillow_format == 'ICO':
                            if ico_size != 'original' and ico_size in ICO_SIZES:
                                frame_image = frame_image.resize(ICO_SIZES[ico_size], Image.LANCZOS)
                            if frame_image.mode not in ('RGB', 'RGBA'):
                                frame_image = frame_image.convert('RGBA')
                        elif pillow_format not in ('PNG', 'GIF', 'WEBP', 'TIFF'):
                            frame_image = frame_image.convert('RGB')

                        frame_buffer = BytesIO()
                        if pillow_format == 'JPEG':
                            frame_image.save(frame_buffer, format='JPEG', quality=100)
                        elif pillow_format == 'ICO':
                            frame_image.save(frame_buffer, format='ICO', sizes=[(frame_image.width, frame_image.height)])
                        else:
                            frame_image.save(frame_buffer, format=pillow_format)

                        frame_filename = f"frame_{str(i+1).zfill(digits)}.{file_extension}"
                        zip_file.writestr(frame_filename, frame_buffer.getvalue())

                        frame_image.close()
                        frame.close()

                new_filename = os.path.splitext(uploaded_file.name)[0] + '_frames.zip'
                content = ContentFile(zip_buffer.getvalue())
            else:
                # Mode conversions
                if pillow_format == 'JPEG':
                    image = image.convert('RGB')
                elif pillow_format == 'BMP':
                    image = image.convert('RGB')
                elif pillow_format == 'ICO':
                    if ico_size != 'original' and ico_size in ICO_SIZES:
                        image = image.resize(ICO_SIZES[ico_size], Image.LANCZOS)
                    if image.mode not in ('RGB', 'RGBA'):
                        image = image.convert('RGBA')
                elif pillow_format not in ('PNG', 'GIF', 'WEBP', 'TIFF'):
                    image = image.convert('RGB')

                buffer = BytesIO()
                if pillow_format == 'JPEG':
                    image.save(buffer, format='JPEG', quality=100)
                elif pillow_format == 'ICO':
                    image.save(buffer, format='ICO', sizes=[(image.width, image.height)])
                else:
                    image.save(buffer, format=pillow_format)

                new_filename = os.path.splitext(uploaded_file.name)[0] + '.' + file_extension
                content = ContentFile(buffer.getvalue())

            converted.converted_image.save(new_filename, content, save=False)
            converted.converted_file_size = content.size
            converted.save()

            return redirect('home')

    images = ConvertedImage.objects.all().order_by('-uploaded_at')
    return render(request, 'imagevault/home.html', {'images': images})


def preview_image(request):
    if request.method == 'POST' and request.FILES.get('image'):
        image = Image.open(request.FILES['image'])
        image.thumbnail((400, 300))
        if image.mode not in ('RGB', 'RGBA'):
            image = image.convert('RGB')
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        return JsonResponse({'preview': f'data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode()}'})
    return JsonResponse({'error': 'No image uploaded'}, status=400)


def delete_image(request, id):
    image = get_object_or_404(ConvertedImage, id=id)
    for f in [image.original_image, image.converted_image]:
        if f and os.path.isfile(f.path):
            os.remove(f.path)
    image.delete()
    return redirect('home')