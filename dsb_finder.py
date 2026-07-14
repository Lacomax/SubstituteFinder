import requests, json, os, re, sys
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Legacy Windows consoles (cp1252) can't encode the emoji in the summary;
# degrade unsupported characters to '?' instead of crashing.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")
os.makedirs("results", exist_ok=True)
os.makedirs("debug", exist_ok=True)

def load_json_file(filename):
    try: return json.load(open(filename, 'r', encoding='utf-8'))
    except Exception as e: return {}

CONFIG = load_json_file("config.json")

def class_variants(cls):
    # "7d" -> ["7d", "7D", "7.d", "7.D"], the forms the plan uses
    base = cls.lower()
    return [base, base.upper(), f"{base[:-1]}.{base[-1]}", f"{base[:-1]}.{base[-1].upper()}"]

def target_classes_for(children):
    return [v for ch in children for v in class_variants(ch['class'])]

CHILDREN = CONFIG.get('children', [])
BASE_CLASSES = [ch['class'].lower() for ch in CHILDREN]
TARGET_CLASSES = target_classes_for(CHILDREN)
CLASS_TO_CHILD = {ch['class'].lower(): ch['name'] for ch in CHILDREN}
EXCLUDED_BY_CLASS = {ch['class'].lower(): {s.lower() for s in ch.get('excluded_subjects', [])}
                     for ch in CHILDREN}

def get_credentials(config=None):
    cfg = CONFIG if config is None else config
    creds = cfg.get('credentials', {})
    username = os.environ.get('DSB_USERNAME') or creds.get('username')
    password = os.environ.get('DSB_PASSWORD') or creds.get('password')
    return username, password

def load_subject_mapping(filename):
    # Lookups lowercase the subject code, so normalize the keys here to
    # tolerate mixed-case entries in the file (e.g. "DaZ-plus7/intf").
    return {k.lower(): v for k, v in load_json_file(filename).items()}

SUBJECT_MAPPING = load_subject_mapping("data/subject_mapping.json")
TEACHER_MAP = load_json_file("data/teacher_map.json")
CLASS_SCHEDULES = {}

for class_file in [ch.get('schedule') for ch in CHILDREN if ch.get('schedule')]:
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
    
    # Canceled = both teacher cells striked and equal, or the Text column
    # says so. Same teacher without strikes is a subject/room change.
    teachers_striked = entry.get('is_original_striked', False) and entry.get('is_substitute_striked', False)
    notes_say_canceled = bool(re.search(r'entf[aä]ll|ausfall|cancel', entry.get('notes', ''), re.IGNORECASE))

    if (original_teacher and substitute_teacher and original_teacher == substitute_teacher and teachers_striked) or notes_say_canceled:
        entry['is_canceled'] = True
        entry['cancel_reason'] = "ENTFALL"
    
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
                    is_original_striked = bool(strike_original)
                    is_substitute_striked = bool(cells[2].find('strike'))

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
                        "is_original_striked": is_original_striked,
                        "is_substitute_striked": is_substitute_striked,
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
                    alternation = '|'.join(re.escape(tc) for tc in sorted(target_classes, key=len, reverse=True))
                    fallback_match = re.match(rf'^({alternation})(\d)([A-Z]{{2,4}})([A-Z]{{2,4}})(E\d{{2}})$', raw_text)
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
                # All pages of a plan share the child title, so key the dump
                # by the page name from the URL (subst_001, subst_002, ...).
                page_name = os.path.splitext(os.path.basename(url.split('?')[0]))[0]
                debug_filename = f"debug/html_{title.replace(' ', '_').replace(':', '_')}_{page_name}.html"
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
                    for base in sorted({tc.lower() for tc in target_classes}, key=len, reverse=True):
                        if len(normalized_class) > len(base) and normalized_class.startswith(base):
                            normalized_class = base
                            break
                    
                    entry = enhance_with_schedule(entry, normalized_class)
                    entry = enhance_entry_details(entry)
                    
                    if class_name not in plan_results:
                        plan_results[class_name] = []
                    plan_results[class_name].append(entry)
                
            except Exception as url_error:
                print(f"Error processing URL {url}: {url_error}")
            
            # A plan can span several subst_NNN.htm pages sharing the same
            # date title, so merge per class instead of overwriting the date.
            if plan_results:
                date_results = all_results.setdefault(date_str, {})
                for cls, entries in plan_results.items():
                    date_results.setdefault(cls, []).extend(entries)
            
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

def filter_excluded_subjects(results, excluded_by_class=None):
    """Drop plan entries for subjects the child does not attend.

    Shared slots (k/ev/eth, DaZ-plus7/intf...) produce one plan row per
    group, but each child only attends one of them; the others are listed
    in the child's excluded_subjects in config.json. A term matches when
    it equals the entry's subject code or full name, case-insensitively —
    never by substring, so 'l' (Latein) leaves 'lint' alone."""
    excluded_map = EXCLUDED_BY_CLASS if excluded_by_class is None else excluded_by_class
    filtered = {}
    for date_str, classes in results.items():
        kept_classes = {}
        for class_name, entries in classes.items():
            excluded = excluded_map.get(class_name.lower(), set())
            kept = [e for e in entries
                    if e.get('subject', '').lower() not in excluded
                    and e.get('subject_full', '').lower() not in excluded]
            if kept:
                kept_classes[class_name] = kept
        if kept_classes:
            filtered[date_str] = kept_classes
    return filtered

def display_subject(entry):
    """Headline subject for an entry, qualified when the slot is shared.

    In shared slots (k/ev/eth, sw/sm...) the regular timetable name is the
    same for every group, so two canceled groups in the same period would
    render as identical lines; append the plan's own subject to tell them
    apart."""
    regular = entry.get('regular_subject_full', '')
    actual = entry.get('subject_full', '') or entry.get('subject', '')
    if regular and actual and actual != regular:
        return f"{regular} – {actual}"
    return regular or actual

def print_summary(results):
    if not results:
        print("\n✅ Sin cambios - No hay sustituciones ni cancelaciones")
        return

    class_to_child = CLASS_TO_CHILD
    all_classes = BASE_CLASSES or sorted({c for classes in results.values() for c in classes})

    # Agrupar por fecha
    for date_str in sorted(results.keys()):
        print(f"\n{'='*10}")
        print(f"📅 {date_str}")
        print('='*10)

        classes = results[date_str]

        # Mostrar cada clase (hijo)
        for class_name in all_classes:
            child_name = class_to_child.get(class_name, class_name.upper())

            if class_name in classes:
                entries = classes[class_name]
                print(f"\n  📚 {child_name} ({class_name}):")

                sorted_entries = sorted(entries, key=lambda x: int(x.get('period', '0')) if x.get('period', '0').isdigit() else 0)

                for entry in sorted_entries:
                    period = entry.get('period', '')

                    # Obtener asignatura y aula
                    subject = display_subject(entry)

                    regular_room = entry.get('regular_room', '')
                    room = entry.get('room', '')
                    room_info = regular_room or room or '---'

                    is_canceled = entry.get('is_canceled', False)

                    # Información del profesor (sin asignatura para el original)
                    original_teacher_full = entry.get('original_teacher_full', '')
                    original_teacher_code = entry.get('original_teacher', '')

                    # Extraer solo el nombre del profesor original (sin la asignatura)
                    if original_teacher_full and '(' in original_teacher_full:
                        original_teacher = original_teacher_full.split('(')[0].strip()
                    else:
                        original_teacher = original_teacher_full or original_teacher_code

                    substitute = entry.get('substitute_full', '') or entry.get('substitute', '')

                    # Formato compacto
                    if is_canceled:
                        print(f"    ❌ Period {period}: {subject} ({room_info})")
                        print(f"       CANCELADA")
                        if entry.get('notes', ''):
                            print(f"       {entry.get('notes', '')}")
                    else:
                        print(f"    🔄 Period {period}: {subject} ({room_info})")
                        same_teacher = entry.get('original_teacher', '') and entry.get('original_teacher', '') == entry.get('substitute', '')
                        if same_teacher:
                            new_subject = entry.get('subject_full', '') or entry.get('subject', '')
                            new_room = entry.get('room', '') or '---'
                            print(f"       Cambio: {new_subject} en {new_room}")
                        elif original_teacher and substitute:
                            print(f"       {original_teacher} ->")
                            print(f"       {substitute}")
                        elif substitute:
                            print(f"       Sustituto: {substitute}")

                        if entry.get('notes', ''):
                            print(f"       Nota: {entry.get('notes', '')}")
            else:
                print(f"\n  📚 {child_name} ({class_name}): ✅ Sin cambios")

    print()

def entry_key(date_str, class_name, entry):
    return (date_str, class_name, entry.get('period', ''), entry.get('subject', ''),
            entry.get('original_teacher', ''), entry.get('substitute', ''),
            entry.get('room', ''), entry.get('notes', ''))

def diff_new_entries(old_results, new_results):
    """Entries in new_results that were not present in old_results."""
    old_keys = {entry_key(d, c, e)
                for d, classes in (old_results or {}).items()
                for c, entries in classes.items()
                for e in entries}
    return [(d, c, e)
            for d, classes in new_results.items()
            for c, entries in classes.items()
            for e in entries
            if entry_key(d, c, e) not in old_keys]

def compose_notification(new_entries, class_to_child=None):
    mapping = CLASS_TO_CHILD if class_to_child is None else class_to_child
    lines = []
    for date_str, class_name, e in new_entries:
        child = mapping.get(class_name.lower(), class_name)
        subject = display_subject(e)
        period = e.get('period', '')
        if e.get('is_canceled'):
            lines.append(f"❌ {child} {date_str}: {subject} (hora {period}) CANCELADA")
        elif e.get('original_teacher', '') and e.get('original_teacher', '') == e.get('substitute', ''):
            new_subject = e.get('subject_full') or subject
            lines.append(f"🔄 {child} {date_str}: hora {period} cambio a {new_subject} en {e.get('room', '---')}")
        else:
            substitute = e.get('substitute_full') or e.get('substitute', '')
            lines.append(f"🔄 {child} {date_str}: {subject} (hora {period}) sustituye {substitute}")
    return '\n'.join(lines)

def send_notification(message, notify_cfg=None):
    cfg = CONFIG.get('notify', {}) if notify_cfg is None else notify_cfg
    method = cfg.get('method', 'none')
    try:
        if method == 'ntfy' and cfg.get('topic'):
            requests.post(f"https://ntfy.sh/{cfg['topic']}",
                          data=message.encode('utf-8'),
                          headers={'Title': 'Plan de sustituciones'},
                          timeout=15)
            return True
        if method == 'termux':
            import subprocess
            subprocess.run(['termux-notification', '-t', 'Plan de sustituciones',
                            '-c', message], check=False)
            return True
    except Exception as e:
        print(f"Error sending notification: {e}")
    return False

def main():
    username, password = get_credentials()
    if not username or not password:
        print("Faltan credenciales DSB: copia config.example.json a config.json "
              "y rellena usuario/contraseña, o define DSB_USERNAME y DSB_PASSWORD.")
        return
    if not TARGET_CLASSES:
        print("No hay hijos/clases configurados: revisa 'children' en config.json.")
        return
    target_classes = TARGET_CLASSES
    
    json_data, session = fetch_dsb_data(username, password)
    if not json_data:
        print("Couldn't get data")
        return
    
    raw_results = extract_timetable_info(json_data, session, target_classes)
    formatted_results = filter_excluded_subjects(format_results(raw_results, target_classes))
    print_summary(formatted_results)

    previous_results = load_json_file(os.path.join("results", "dsb_results.json"))
    new_entries = diff_new_entries(previous_results, formatted_results)

    save_path = save_results(formatted_results)
    if save_path:
        print(f"\nComplete details saved in: {save_path}")

    if new_entries:
        print(f"🔔 {len(new_entries)} cambio(s) nuevo(s) desde la última ejecución")
        if send_notification(compose_notification(new_entries)):
            print("Notificación enviada")

if __name__ == "__main__":
    main()