from django import template

register = template.Library()

@register.inclusion_tag('ArslanTakipApp/comment_template.html')
def render_comment(node):
    # {'node': {'comment': <Comment: Comment object (406)>, 'replies': [{'comment': <Comment: Comment object (407)>}]}} formatında olmalı
    return {'node': node}