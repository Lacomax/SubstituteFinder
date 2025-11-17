import requests, json, os, re
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
os.makedirs("results", exist_ok=True)
os.makedirs("debug", exist_ok=True)

def load_json_file(filename):
    try: return json.load(open(filename, 'r', encoding='utf-8'))
    except Exception as e: return {}

SUBJECT_MAPPING = load_json_file("data/subject_mapping.json")
TEACHER_MAP = load_json_file("data/teacher_map.json")
CLASS_SCHEDULES = {}

for class_file in ['data/7d.json', 'data/7e.json']:
    try:
        data = load_json_file(class_file)
        class_name = data.get('clase', '').lower()
        if class_name:
            schedule = {}
            for event in data.get('eventos', []):
                day_num = event.get('dia', 0)
                period = str(event.get('periodo', ''))
                day_names = ['', 'Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag']
                day_name = day_names[day_num] if 0 < day_num < len(day_names) else f"Day {day_num}"
                if day_name not in schedule: schedule[day_name] = {}
                schedule[day_name][period] = {
                    'subject': event.get('asignatura', ''),
                    'room': event.get('aula', ''),
                    'teacher': event.get('profesor', '')
                }
            CLASS_SCHEDULES[class_name] = schedule
    except Exception as e:
        print(f"Error processing schedule {class_file}: {e}")

def fetch_dsb_data(username, password):
    try:
        auth_url = f"https://mobileapi.dsbcontrol.de/authid?user={username}&password={password}&bundleid=de.heinekingmedia.dsbmobile&appversion=35&osversion=22&pushid="
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json'
        }
        
        auth_response = requests.get(auth_url, headers=headers, timeout=15, verify=False)
        auth_response.raise_for_status()
        auth_id = auth_response.text.strip('"')
        
        if not auth_id or len(auth_id) < 10:
            print(f"Authentication error: {auth_response.text}")
            return None, None
            
        timetables_url = f"https://mobileapi.dsbcontrol.de/dsbtimetables?authid={auth_id}"
        response = requests.get(timetables_url, headers=headers, timeout=15, verify=False)
        response.raise_for_status()
        
        with open("debug/json_response.json", "w", encoding="utf-8") as f:
            json.dump(response.json(), f, ensure_ascii=False, indent=2)
        
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        })
        session.verify = False
        
        return response.json(), session
    except Exception as e:
        print(f"Error getting data: {e}")
        return None, None

def is_target_class(class_text, target_classes):
    if not class_text: return False
    class_text = class_text.strip()
    if class_text in target_classes: return True
    
    for target in target_classes:
        patterns = [f"^{target}$", f"^{target},", f", {target}$", f", {target},", f"^{target} ", f" {target}$"]
        if any(re.search(pattern, class_text) for pattern in patterns):
            return True
    return False

def extract_date(soup):
    title_elem = soup.find('div', class_='mon_title')
    if not title_elem: return "Unknown date"
    return re.sub(r'\s*\(.*?\)\s*', '', title_elem.text.strip()).strip()

def extract_day_of_week(date_str):
    day_match = re.search(r'(\w+)$', date_str)
    if day_match:
        day = day_match.group(1)
        days_mapping = {
            'Monday': 'Montag', 'Tuesday': 'Dienstag', 'Wednesday': 'Mittwoch',
            'Thursday': 'Donnerstag', 'Friday': 'Freitag', 'Saturday': 'Samstag', 'Sunday': 'Sonntag'
        }
        return days_mapping.get(day, day)
    return "Unknown"

def enhance_with_schedule(entry, class_name):
    short_class = class_name.lower()
    day_of_week = extract_day_of_week(entry.get('date', ''))
    period = entry.get('period', '')
    
    if short_class in CLASS_SCHEDULES and day_of_week in CLASS_SCHEDULES[short_class] and period in CLASS_SCHEDULES[short_class][day_of_week]:
        schedule_info = CLASS_SCHEDULES[short_class][day_of_week][period]
        
        if not entry.get('subject'): entry['subject'] = schedule_info.get('subject', '')
        
        entry['regular_subject'] = schedule_info.get('subject', '')
        entry['regular_room'] = schedule_info.get('room', '')
        entry['regular_teacher_code'] = schedule_info.get('teacher', '')
        
        teacher_codes = schedule_info.get('teacher', '').split('/')
        teacher_names = [f"{TEACHER_MAP[code][0]} ({TEACHER_MAP[code][1]})" if code and code in TEACHER_MAP else code for code in teacher_codes if code]
        
        if teacher_names: entry['regular_teacher'] = '/'.join(teacher_names)
    
    return entry

def enhance_entry_details(entry):
    if not entry.get('subject') and entry.get('original_teacher') in TEACHER_MAP:
        entry['subject'] = TEACHER_MAP[entry['original_teacher']][1].lower()

    if not entry.get('subject') and entry.get('regular_subject'):
        entry['subject'] = entry['regular_subject']

    subject_code = entry.get('subject', '').lower()
    entry['subject_full'] = SUBJECT_MAPPING.get(subject_code, subject_code if subject_code else "No subject")

    regular_subject = entry.get('regular_subject', '').lower()
    entry['regular_subject_full'] = SUBJECT_MAPPING.get(regular_subject, f"{regular_subject} (Unknown)")

    original_teacher = entry.get('original_teacher', '')
    substitute_teacher = entry.get('substitute', '')
    
    # Check for canceled class
    is_subject_striked = entry.get('is_subject_striked', False)
    
    if original_teacher and substitute_teacher and original_teacher == substitute_teacher:
        entry['is_canceled'] = True
        entry['cancel_reason'] = "ENTFALL" if is_subject_striked else "ENTFALL???"
    
    entry['original_teacher_full'] = f"{TEACHER_MAP[original_teacher][0]} ({TEACHER_MAP[original_teacher][1]})" if original_teacher in TEACHER_MAP else f"{original_teacher} (Unknown)" if original_teacher else ''
    
    entry['substitute_full'] = f"{TEACHER_MAP[substitute_teacher][0]} ({TEACHER_MAP[substitute_teacher][1]})" if substitute_teacher in TEACHER_MAP else f"{substitute_teacher} (Unknown)" if substitute_teacher else ''

    return entry

def extract_class_info(soup, target_classes):
    all_entries = []

    for table in soup.find_all('table', class_='mon_list'):
        for row in table.find_all('tr'):
            cells = row.find_all('td', class_='list')
            if len(cells) >= 6:
                class_name = cells[0].text.strip()
                if any(is_target_class(class_name, [tc]) for tc in target_classes):
                    original_cell = cells[3]
                    strike_original = original_cell.find('strike')
                    original_teacher = strike_original.text.strip() if strike_original and strike_original.text.strip() else original_cell.get_text(strip=True)
                    
                    subject_cell = cells[4]
                    is_subject_striked = bool(subject_cell.find('strike'))
                    subject_text = subject_cell.text.strip()

                    entry = {
                        "class": class_name,
                        "period": cells[1].text.strip(),
                        "substitute": cells[2].text.strip(),
                        "original_teacher": original_teacher,
                        "subject": subject_text,
                        "is_subject_striked": is_subject_striked,
                        "room": cells[5].text.strip(),
                        "notes": cells[6].text.strip() if len(cells) > 6 else ""
                    }
                    for cls in class_name.split(','):
                        entry_copy = entry.copy()
                        entry_copy['class'] = cls.strip()
                        all_entries.append(enhance_entry_details(entry_copy))
            else:
                raw_text = re.sub(r'\s+', '', row.text.strip().replace('\xa0', ' ').replace('\u00a0', ' ').replace('\t', ' '))
                if any(tc in raw_text for tc in target_classes):
                    fallback_match = re.match(r'^(7[de])(\d)([A-Z]{2,4})([A-Z]{2,4})(E\d{2})$', raw_text)
                    if fallback_match:
                        class_name, period, substitute, original_teacher, room = fallback_match.groups()
                        entry = {
                            "class": class_name,
                            "period": period,
                            "substitute": substitute,
                            "original_teacher": original_teacher,
                            "subject": "",
                            "is_subject_striked": False,
                            "room": room,
                            "notes": ""
                        }
                        all_entries.append(entry)

    return all_entries

def extract_timetable_info(json_data, session, target_classes):
    if not json_data: return {}
    
    all_results = {}
    plan_urls = []
    
    try:
        for timetable_group in json_data:
            group_title = timetable_group.get('Title', 'No title')
            
            if 'Childs' in timetable_group and timetable_group['Childs']:
                for child in timetable_group['Childs']:
                    detail_url = child.get('Detail', '')
                    child_title = child.get('Title', 'No title')
                    child_date = child.get('Date', 'Unknown date')
                    full_title = f"{group_title} - {child_title}"
                    
                    if detail_url and detail_url.startswith('http'):
                        plan_urls.append((detail_url, full_title, child_date))
        
        for url, title, date in plan_urls:
            plan_results = {}
            
            try:
                response = session.get(url, timeout=15)
                
                if "406 - Client browser does not accept the MIME type" in response.text:
                    session.headers.update({'Accept': '*/*'})
                    response = session.get(url, timeout=15)
                
                html_content = response.text
                debug_filename = f"debug/html_{title.replace(' ', '_').replace(':', '_')}.html"
                with open(debug_filename, "w", encoding="utf-8") as f:
                    f.write(html_content)
                
                if "406 - Client browser does not accept the MIME type" in html_content:
                    print("Persistent 406 error. The server doesn't accept our headers.")
                    continue
                
                soup = BeautifulSoup(html_content, 'html.parser')
                date_str = extract_date(soup)
                entries = extract_class_info(soup, target_classes)
                
                for entry in entries:
                    class_name = entry['class']
                    entry['date'] = date_str
                    entry['url'] = url
                    entry['day_of_week'] = extract_day_of_week(date_str)
                    
                    normalized_class = class_name.lower()
                    if len(normalized_class) > 2 and normalized_class[:2] in ['7d', '7e']:
                        normalized_class = normalized_class[:2]
                    
                    entry = enhance_with_schedule(entry, normalized_class)
                    entry = enhance_entry_details(entry)
                    
                    if class_name not in plan_results:
                        plan_results[class_name] = []
                    plan_results[class_name].append(entry)
                
            except Exception as url_error:
                print(f"Error processing URL {url}: {url_error}")
            
            if plan_results:
                all_results[date_str] = plan_results
            
        return all_results
        
    except Exception as e:
        print(f"Error extracting timetable information: {e}")
        import traceback
        traceback.print_exc()
        return all_results

def format_results(results, target_classes):
    formatted = {}
    
    for date_str, class_info in results.items():
        target_entries = {}
        for cls, entries in class_info.items():
            for target in target_classes:
                if is_target_class(cls, [target]):
                    if target not in target_entries:
                        target_entries[target] = []
                    target_entries[target].extend(entries)
        
        for class_name in target_entries:
            unique = []
            seen = set()
            for entry in target_entries[class_name]:
                key = (entry.get('period', ''), entry.get('subject', ''), entry.get('room', ''), 
                       entry.get('original_teacher', ''), entry.get('substitute', ''),
                       entry.get('date', ''), entry.get('notes', ''))
                if key not in seen:
                    seen.add(key)
                    unique.append(entry)
            
            target_entries[class_name] = unique
            
        if target_entries:
            formatted[date_str] = target_entries
    
    return formatted

def save_results(results, filename="dsb_results.json"):
    try:
        path = os.path.join("results", filename)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        return path
    except Exception as e:
        print(f"Error saving results: {e}")
        return None

def get_statistics(results):
    """Genera estadísticas de cambios por clase"""
    stats = {}
    for date_str, classes in results.items():
        for class_name, entries in classes.items():
            if class_name not in stats:
                stats[class_name] = {'canceled': 0, 'substituted': 0, 'total': 0}

            for entry in entries:
                stats[class_name]['total'] += 1
                if entry.get('is_canceled', False):
                    stats[class_name]['canceled'] += 1
                else:
                    stats[class_name]['substituted'] += 1
    return stats

def print_summary(results):
    if not results:
        print("\n" + "="*70)
        print("✅ SIN CAMBIOS - No hay sustituciones ni cancelaciones")
        print("="*70)
        return

    # Mapeo de clases a nombres de hijos
    class_to_child = {
        '7d': 'DIEGO',
        '7e': 'MATEO'
    }

    # Generar estadísticas
    stats = get_statistics(results)

    # Imprimir encabezado y resumen
    print("\n" + "="*70)
    print("📊 RESUMEN DE CAMBIOS")
    print("="*70)

    # Asegurar que aparezcan ambas clases
    all_classes = ['7d', '7e']
    for class_name in all_classes:
        child_name = class_to_child.get(class_name, class_name.upper())

        if class_name in stats:
            stat = stats[class_name]
            total = stat['total']
            canceled = stat['canceled']
            substituted = stat['substituted']
            icon = "⚠️"
            print(f"{icon} {child_name} ({class_name}): {total} cambio(s) - {canceled} cancelación(es), {substituted} sustitución(es)")
        else:
            icon = "✅"
            print(f"{icon} {child_name} ({class_name}): Sin cambios")

    print("="*70 + "\n")

    # Agrupar resultados por clase
    results_by_class = {}
    for date_str, classes in results.items():
        for class_name, entries in classes.items():
            if class_name not in results_by_class:
                results_by_class[class_name] = {}
            results_by_class[class_name][date_str] = entries

    # Imprimir resultados por hijo - siempre mostrar ambos
    for class_name in all_classes:
        child_name = class_to_child.get(class_name, class_name.upper())

        print("=" * 70)
        print(f"📚 {child_name} ({class_name.upper()})")
        print("=" * 70)

        if class_name in results_by_class:
            dates_data = results_by_class[class_name]

            for date_str in sorted(dates_data.keys()):
                entries = dates_data[date_str]

                print(f"\n📅 {date_str}")
                print("-" * 70)

                sorted_entries = sorted(entries, key=lambda x: int(x.get('period', '0')) if x.get('period', '0').isdigit() else 0)

                for entry in sorted_entries:
                    period = entry.get('period', '')

                    # Obtener asignatura y aula
                    regular_subject = entry.get('regular_subject_full', '')
                    subject_full = entry.get('subject_full', '')
                    subject = regular_subject or subject_full or entry.get('subject', '')

                    regular_room = entry.get('regular_room', '')
                    room = entry.get('room', '')
                    # Priorizar aula regular si está disponible, luego la del cambio
                    room_info = regular_room or room or '---'

                    is_canceled = entry.get('is_canceled', False)

                    # Icono según tipo de cambio
                    if is_canceled:
                        icon = "❌"
                        change_type = "CANCELADA"
                    else:
                        icon = "🔄"
                        change_type = "SUSTITUCIÓN"

                    # Información del profesor
                    original_teacher = entry.get('original_teacher_full', '') or entry.get('original_teacher', '')
                    substitute = entry.get('substitute_full', '') or entry.get('substitute', '')
                    regular_teacher = entry.get('regular_teacher', '')

                    print(f"\n  {icon} Periodo {period}: {subject}")
                    print(f"     Aula: {room_info}")

                    if is_canceled:
                        print(f"     Estado: {change_type}")
                        cancel_reason = entry.get('cancel_reason', 'ENTFALL')
                        if entry.get('notes', ''):
                            print(f"     Motivo: {entry.get('notes', '')}")
                    else:
                        # Mostrar profesor regular si está disponible
                        if regular_teacher and original_teacher:
                            print(f"     Profesor habitual: {regular_teacher}")

                        if original_teacher and substitute:
                            print(f"     Cambio: {original_teacher} → {substitute}")
                        elif original_teacher:
                            print(f"     Profesor: {original_teacher}")
                        elif substitute:
                            print(f"     Profesor sustituto: {substitute}")

                        if entry.get('notes', ''):
                            print(f"     Nota: {entry.get('notes', '')}")

                print()
        else:
            print("\n  ✅ Sin cambios para esta clase\n")

        print()

def main():
    username, password = "173002", "vplan"
    target_classes = ["7d", "7D", "7.d", "7e", "7E", "7.e"]
    
    json_data, session = fetch_dsb_data(username, password)
    if not json_data:
        print("Couldn't get data")
        return
    
    raw_results = extract_timetable_info(json_data, session, target_classes)
    formatted_results = format_results(raw_results, target_classes)
    print_summary(formatted_results)    
    
    save_path = save_results(formatted_results)    
    if save_path:
        print(f"\nComplete details saved in: {save_path}")

if __name__ == "__main__":
    main()