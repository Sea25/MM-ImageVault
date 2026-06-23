from django.shortcuts import render, redirect, get_object_or_404
from django.core.files.base import ContentFile
from django.http import JsonResponse, HttpResponse
from PIL import Image
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
    '16': (16,16), '32': (32,32), '48': (48,48),
    '64': (64,64), '128': (128,128), '256': (256,256),
}

def convert_single_frame(image, pillow_format, ico_size='original'):
    """Convert a single PIL image to the target format, return BytesIO buffer."""
    img = image.copy()
    if pillow_format == 'JPEG':
        img = img.convert('RGB')
    elif pillow_format == 'BMP':
        img = img.convert('RGB')
    elif pillow_format == 'ICO':
        if ico_size != 'original' and ico_size in ICO_SIZES:
            img = img.resize(ICO_SIZES[ico_size], Image.LANCZOS)
        if img.mode not in ('RGB', 'RGBA'):
            img = img.convert('RGBA')
    elif pillow_format not in ('PNG', 'GIF', 'WEBP', 'TIFF'):
        img = img.convert('RGB')
    buf = BytesIO()
    if pillow_format == 'JPEG':
        img.save(buf, format='JPEG', quality=100)
    elif pillow_format == 'ICO':
        img.save(buf, format='ICO', sizes=[(img.width, img.height)])
    else:
        img.save(buf, format=pillow_format)
    return buf


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
            base_name = os.path.splitext(uploaded_file.name)[0]

            # Check if input is an animated GIF
            is_animated_gif = (
                getattr(image, 'format', '') == 'GIF' and
                hasattr(image, 'n_frames') and
                image.n_frames > 1
            )

            if is_animated_gif and pillow_format != 'GIF':
                # Extract all frames, convert each, bundle into ZIP
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for i in range(image.n_frames):
                        image.seek(i)
                        frame_buf = convert_single_frame(image, pillow_format, ico_size)
                        zf.writestr(f'frame_{i+1:03d}.{file_extension}', frame_buf.getvalue())

                zip_filename = base_name + '_frames.zip'
                content = ContentFile(zip_buffer.getvalue())
                converted.converted_image.save(zip_filename, content, save=False)
                converted.converted_file_size = content.size
                converted.output_format = output_format + '_ZIP'  # mark as zip
                converted.save()

            elif pillow_format == 'GIF':
                # Output is GIF — preserve animation
                image.seek(0)
                frames = []
                try:
                    while True:
                        frames.append(image.copy())
                        image.seek(image.tell() + 1)
                except EOFError:
                    pass
                buf = BytesIO()
                if len(frames) > 1:
                    frames[0].save(buf, format='GIF', save_all=True,
                                   append_images=frames[1:], loop=0)
                else:
                    frames[0].save(buf, format='GIF')
                content = ContentFile(buf.getvalue())
                converted.converted_image.save(base_name + '.gif', content, save=False)
                converted.converted_file_size = content.size
                converted.save()

            else:
                # Normal single image conversion
                image.seek(0) if hasattr(image, 'seek') else None
                buf = convert_single_frame(image, pillow_format, ico_size)
                content = ContentFile(buf.getvalue())
                converted.converted_image.save(base_name + '.' + file_extension, content, save=False)
                converted.converted_file_size = content.size
                converted.save()

            return redirect('home')

    images = ConvertedImage.objects.all().order_by('-uploaded_at')
    return render(request, 'imagevault/home.html', {'images': images})


def preview_image(request):
    """Backend preview for TIFF, HEIC, HEIF."""
    if request.method == 'POST' and request.FILES.get('image'):
        try:
            image = Image.open(request.FILES['image'])
            try:
                image.seek(0)
            except (AttributeError, EOFError):
                pass
            image.thumbnail((400, 300))
            if image.mode not in ('RGB', 'RGBA'):
                image = image.convert('RGB')
            buf = BytesIO()
            image.save(buf, format='PNG')
            return JsonResponse({'preview': f'data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'No image uploaded'}, status=400)


def delete_image(request, id):
    record = get_object_or_404(ConvertedImage, id=id)
    for f in [record.original_image, record.converted_image]:
        if f and os.path.isfile(f.path):
            os.remove(f.path)
    record.delete()
    return redirect('home')