import os

app_views = r'c:\Users\beyza.ozkara\ArslanDjango\env\ArslanProject\ArslanTakipApp\views.py'
event_data_html = r'c:\Users\beyza.ozkara\ArslanDjango\env\ArslanProject\ArslanTakipApp\templates\ArslanTakipApp\event_data.html'
hesaplama_html = r'c:\Users\beyza.ozkara\ArslanDjango\env\ArslanProject\ArslanTakipApp\templates\4500\hesaplama.html'

def replace_in_file(path, old, new):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    new_content = content.replace(old, new)
    if content != new_content:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f'Updated {path}')

replace_in_file(app_views, "render(request, 'DMS/event_data.html')", "render(request, 'ArslanTakipApp/event_data.html')")
replace_in_file(event_data_html, "'DMS:api_get_event_data'", "'ArslanTakipApp:api_get_event_data'")
replace_in_file(event_data_html, "'DMS:api_update_event_data'", "'ArslanTakipApp:api_update_event_data'")
replace_in_file(event_data_html, "'DMS:api_get_kalip_nos'", "'ArslanTakipApp:api_get_kalip_nos'")
replace_in_file(hesaplama_html, "'DMS:event_data'", "'ArslanTakipApp:event_data'")
