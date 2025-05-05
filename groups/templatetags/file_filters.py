from django import template

register = template.Library()

@register.filter
def file_extension(value):
    """Возвращает расширение файла в нижнем регистре"""
    return value.split('.')[-1].lower() if '.' in value else 'file'

@register.filter
def is_image(value):
    """Проверяет, является ли файл изображением"""
    ext = value.split('.')[-1].lower() if '.' in value else ''
    return ext in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp']