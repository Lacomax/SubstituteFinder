import requests
from bs4 import BeautifulSoup
import urllib3
import json
import os
import re
from datetime import datetime

# Deshabilitar advertencias SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Crear directorios para resultados y depuración
os.makedirs("results", exist_ok=True)
os.makedirs("debug", exist_ok=True)

# Mapeo de abreviaturas de materias a nombres completos
SUBJECT_MAPPING = {
    'd': 'Deutsch',
    'e': 'Englisch',
    'g': 'Geschichte',
    'f': 'Französisch',
    'l': 'Latein',
    'f/l': 'Französisch', #'Französisch/Latein',
    'l/f': 'Französisch',#'Latein/Französisch',
    'm': 'Mathematik',
    'ku': 'Kunst',
    'mu': 'Musik',
    'ntbio': 'Natur und Technik (Bio)',
    'ntinf': 'Natur und Technik (Informatik)',
    'ev': 'Evang. Religionslehre',
    'k': 'Kath. Religionslehre',
    'eth': 'Ethik',
    'eth/ev/k': 'Religion',
    'eth/k/ev': 'Religion',
    'ev/eth/k': 'Religion',
    'ev/k/eth': 'Religion',
    'k/ev/eth': 'Religion',
    'k/eth/ev': 'Religion',
    'sw': 'Sport weiblich',
    'sm': 'Sport männlich',
    'mint': 'Mathe Intensiv',
    'mint/mint': 'Mathe Intensiv',
    'fint': 'Französisch Intensiv',
    'lint/fint/fint': 'Französisch Intensiv',#'Latein/Französisch',
    'fint/fint/lint': 'Französisch Intensiv',#'Latein/Französisch',
    'lint': 'Latein Intensiv',
    'qhu': 'Qualifizierter Hausunterricht',
    'qhu6': 'Qualifizierter Hausunterricht Kl. 6',
    'ffmm-gta': 'Förderung Math. männlich GTA',
    'ffmd-gta': 'Förderung Math. Deutsch GTA',
    'ffme-gta': 'Förderung Math. Englisch GTA'
}

# Mapeo de abreviaturas de profesores a nombres completos
TEACHER_MAP = {
    'AB': ('Louisa Abdelkader', ''),
    'Acher': ('Micha Acher', ''),
    'AK': ('Julia Akodad', ''),
    'AS': ('Deborah Aschoff', ''),
    'AU': ('Lavinia Auer', 'Ethik'),
    'BA': ('Sandra Baumann', ''),
    'BC': ('Magdalena Bach', ''),
    'BF': ('Petra Bergfeld', ''),
    'BL': ('Clara Blanz', ''),
    'BLA': ('Philip Blayney', ''),
    'BO': ('Robert Boscher', ''),
    'BR': ('Katharina Berger', ''),
    'BS': ('Stephan Bertelsmann', ''),
    'BSC': ('Eva-Maria Bschorr', ''),
    'BU': ('Veronika Burkholz', ''),
    'BY': ('Seda Baysal', 'Geschichte'),
    'BZ': ('Natalya Berezovskaia', ''),
    'CA': ('Verena Callegari-Hofmann', ''),
    'CAS': ('Bruce Casal', ''),
    'CAV': ('Julia Cavalcante Dorner', ''),
    'DA': ('Ina Dahlhaus', ''),
    'DD': ('Dominik Draxler', ''),
    'DE': ('Stefanie Deßloch', ''),
    'DL': ('Dominik Dhillon', ''),
    'DOE': ('Amelie Döring', 'Kath. Religionslehre'),
    'DR': ('Jan Dreyer', ''),
    'DRE': ('Anastasia Dreher', ''),
    'DUE': ('Max Dürr', ''),
    'DX': ('Irene Daxecker-Sproesser', ''),
    'EG': ('Amerina Engel', ''),
    'EGH': ('Jasmin Eghbaly', 'Ethik'),
    'EIH': ('Verena Eihoff', 'Mathematik'),
    'EN': ('Maximilian Engl', ''),
    'EY': ('Oliver Eyding', 'Natur und Technik/Geschichte'),
    'FL': ('Clarissa Ferstl', ''),
    'GB': ('Christiane Gruber', ''),
    'GD': ('Philipp Goldammer', ''),
    'GF': ('Christine Görner-Fliß', 'Kunst'),
    'GLI': ('Elena Glik', ''),
    'GN': ('Korbinian Günther', 'Französisch'),
    'GP': ('Claus-Marco Göppner', ''),
    'GR': ('Mariella Giesriegl', ''),
    'GRA': ('Laura Grabelus', ''),
    'GT': ('Anna Güntner', ''),
    'GU': ('Aurélie Günther', ''),
    'HA': ('Stefan Haas', ''),
    'HAH': ('Maximilian Hahn', ''),
    'HAU': ('Gerlinde Hautz', ''),
    'HB': ('Gerhard Huber', ''),
    'HD': ('Nathalie Hausdorf', ''),
    'HF': ('Dominik Hofmann', ''),
    'HG': ('Tyll Herget', ''),
    'HIR': ('Judith Hirsch', ''),
    'HM': ('Gero Hermannstaller', 'Sport'),
    'HO': ('Andrea Hotop', 'Natur und Technik'),
    'HR': ('Adelheid Harder', ''),
    'HS': ('Annemarie Hesse', ''),
    'HT': ('Veronika Härter', ''),
    'HU': ('Carola Hartmannsgruber', ''),
    'JAU': ('Korbinian Jaud', ''),
    'Jonas': ('Johanna Jonas', ''),
    'JW': ('Dorothee Jacquot-Weber', ''),
    'KB': ('Torsten Kuchenbecker', ''),
    'KC': ('Sabine Kolbeck', 'Deutsch'),
    'KI': ('Ralf Kienzle', ''),
    'KL': ('Ines Klante', ''),
    'KLE': ('Julia Kleber', ''),
    'KO': ('Edith Kosakowski', ''),
    'KP': ('Cornelia Kapsner', ''),
    'KR': ('Thomas Kraemer', ''),
    'KUE': ('Jenny Kühl', 'Musik'),
    'KUH': ('Stefan Küchemann', ''),
    'KW': ('Claudia Kantwill-Hoffmann', ''),
    'LAN': ('Christine Lanzinger', 'Musik'),
    'LBH': ('Andrea Liebhauser', ''),
    'LC': ('Beate Leclair', 'Sport'),
    'LE': ('Florian Leszynsky', 'Sport'),
    'Legisa': ('Vasja Legisa', ''),
    'LEH': ('Philipp Lehmann', ''),
    'LEO': ('Alexandra Leopold', 'Kath. Religionslehre'),
    'LIN': ('Tobias Linner', ''),
    'LM': ('Marco Lemppenau', ''),
    'MA': ('Falco Maier', ''),
    'MC': ('Yvonne Marcuse', ''),
    'ME': ('Larissa Mende', ''),
    'MG': ('Katrin Morgan', ''),
    'MH': ('Raphael Mayrhofer', ''),
    'MLD': ('Lutz Mailänder', ''),
    'MO': ('Martina Molitor', 'Sport'),
    'NE': ('Andreas Nerl', 'Englisch'),
    'Neuman': ('Petra Neumann', ''),
    'NM': ('Pascal Neumann', ''),
    'PA': ('Elena Pfaff', ''),
    'PF': ('Robert Pfaffel', ''),
    'PTA': ('Anuschka Ptacek', ''),
    'QUA': ('Corinna Quaas', ''),
    'RA': ('Katharina Rabe', ''),
    'RAU': ('Sonja Rauscher', ''),
    'RBL': ('Annalena Rebele', 'Kunst'),
    'RE': ('Marietheres Rebele', ''),
    'REI': ('Gunther Reimann', ''),
    'RI': ('Thomas Rieger', ''),
    'RL': ('Unbekannter Lehrer', 'Kunst'),
    'RM': ('Insa Remmers', ''),
    'RN': ('Maren Reinicke', 'Französisch'),
    'ROE': ('Sonja Röhrle', 'Kath. Religionslehre'),
    'RW': ('Annett Runnwerth', ''),
    'S': ('Std-Plan Stundenplan', ''),
    'SB': ('Heidrun Siller-Brabant', ''),
    'SC': ('Peter Schmidbauer', ''),
    'Schlic': ('Wolfgang Schlick', ''),
    'Schnei': ('Stefan Schneider', ''),
    'SCM': ('Thomas Schmidt', ''),
    'SEM': ('Stephanie Semmlinger', ''),
    'SF': ('Stefan Singer', ''),
    'SH': ('Annette Schmidt', ''),
    'SI': ('Marie-Luise Steinmann', 'Evang. Religionslehre'),
    'SL': ('Claudia Schöttl', ''),
    'SM': ('Benedikt Singhammer', 'Mathematik/Natur und Technik'),
    'SOK': ('Ondrej Sokola', 'Natur und Technik'),
    'SP': ('Laura Sieper-Burggraf', ''),
    'SR': ('Monika Stadler-Huber', ''),
    'ST': ('Andreas Seibt', ''),
    'SU': ('Kerstin Schurogailo', ''),
    'SWA': ('Lothar Schwab', ''),
    'SX': ('Sabine Seitz', 'Ethik'),
    'SY': ('Monika-Yvonne Stein', ''),
    'SZ': ('Michelle Schmidt', 'Mathematik'),
    'TA': ('Marlen Thaler', 'Latein'),
    'TB': ('Sonja Theobald', 'Sport'),
    'TEU': ('Doris Teuber', ''),
    'TH': ('Benjamin Thumm', ''),
    'THI': ('Dana Thielen', ''),
    'TO': ('Susanne Torres', 'Englisch'),
    'TRE': ('Manuel Trenkle', ''),
    'TSA': ('Dimitri Tsambrounis', ''),
    'TX': ('Jochen Trux', ''),
    'TZ': ('Gerhard Tietz', ''),
    'V': ('V-Plan Vertretungsplan', ''),
    'WAG': ('Maximilian Wagner', ''),
    'Wagner': ('Lucia Wagner', ''),
    'WD': ('Corbinian Weindorf', ''),
    'WDS': ('Terry Woods', 'Französisch'),
    'WEI': ('Jule Weiss', ''),
    'WG': ('Arthur Weigl', ''),
    'WIL': ('Yannick Wille', ''),
    'WS': ('Monika Weiser', 'Latein'),
    'ZI': ('Sarah Ziegeler', 'Deutsch'),
    'ZIM': ('Thomas Zimmermann', '')
}

# Mapeo específico para 6d
TEACHER_6D = {
    'KC': TEACHER_MAP['KC'],
    'WS': TEACHER_MAP['WS'],
    'NE': TEACHER_MAP['NE'],
    'GN': TEACHER_MAP['GN'],
    'WDS': TEACHER_MAP['WDS'],
    'EIH': TEACHER_MAP['EIH'],
    'SZ': TEACHER_MAP['SZ'],
    'EY': TEACHER_MAP['EY'],
    'HO': TEACHER_MAP['HO'],
    'RBL': TEACHER_MAP['RBL'],
    'GF': TEACHER_MAP['GF'],
    'LAN': TEACHER_MAP['LAN'],
    'LC': TEACHER_MAP['LC'],
    'HM': TEACHER_MAP['HM'],
    'MO': TEACHER_MAP['MO'],
    'SI': TEACHER_MAP['SI'],
    'LEO': TEACHER_MAP['LEO'],
    'ROE': TEACHER_MAP['ROE'],
    'SX': TEACHER_MAP['SX']
}

# Mapeo específico para 6e
TEACHER_6E = {
    'ZI': TEACHER_MAP['ZI'],
    'TA': TEACHER_MAP['TA'],
    'TO': TEACHER_MAP['TO'],
    'RN': TEACHER_MAP['RN'],
    'WDS': TEACHER_MAP['WDS'],
    'SM': TEACHER_MAP['SM'],
    'SZ': TEACHER_MAP['SZ'],
    'SOK': TEACHER_MAP['SOK'],
    'BY': TEACHER_MAP['BY'],
    'GF': TEACHER_MAP['GF'],
    'KUE': TEACHER_MAP['KUE'],
    'TB': TEACHER_MAP['TB'],
    'HM': TEACHER_MAP['HM'],
    'LE': TEACHER_MAP['LE'],
    'MO': TEACHER_MAP['MO'],
    'LC': TEACHER_MAP['LC'],
    'SI': TEACHER_MAP['SI'],
    'DOE': TEACHER_MAP['DOE'],
    'AU': TEACHER_MAP['AU'],
    'EGH': TEACHER_MAP['EGH']
}

# Usar el mapeo completo para todos los profesores
ALL_TEACHERS = TEACHER_MAP

# Mapeo de aulas a ubicaciones
ROOM_MAPPING = {
    'N7': 'Raum N7',
    'N8': 'Raum N8',
    'E01': 'Raum E01',
    'TH4': 'Turnhalle 4',
    'TH2': 'Turnhalle 2',
    'A307': 'Raum A307',
    'C15': 'Raum C15',
    'A103': 'Raum A103',
    'B104': 'Raum B104',
    'N6': 'Raum N6',
    'B5': 'Raum B5',
    'N5': 'Raum N5',
    'E06': 'Raum E06',
    'E07': 'Raum E07',
    'N4': 'Raum N4'
}

# Horarios regulares por clase
CLASS_SCHEDULES = {
    '6d': {
        'Montag': {
            '1': {'subject': 'g', 'room': 'N7', 'teacher': 'EG'},
            '2': {'subject': 'f/l', 'room': 'N7/E01', 'teacher': 'GT/WS'},
            '3': {'subject': 'sw/sm', 'room': 'TH4/TH2', 'teacher': 'MR/HM'},
            '4': {'subject': 'sm/sw', 'room': 'TH2/TH4', 'teacher': 'HM/MR'},
            '5': {'subject': 'ku', 'room': 'B104', 'teacher': 'RL'},
            '6': {'subject': 'ku', 'room': 'B104', 'teacher': 'RL'},
            '7': {'subject': 'mittag', 'room': '', 'teacher': ''},
            '8': {'subject': 'qhu6', 'room': 'N7', 'teacher': ''},
            '9': {'subject': 'ffmm-gta', 'room': 'N7', 'teacher': ''}
        },
        'Dienstag': {
            '1': {'subject': 'e', 'room': 'N7', 'teacher': 'NL'},
            '2': {'subject': 'ntbio', 'room': 'N7', 'teacher': 'HP'},
            '3': {'subject': 'd', 'room': 'N7', 'teacher': 'KK'},
            '4': {'subject': 'm', 'room': 'N7', 'teacher': 'EF'},
            '5': {'subject': 'ev/eth/k', 'room': 'N6/B5/N5', 'teacher': 'SM/SZ/RE'},
            '6': {'subject': 'ev/eth/k', 'room': 'N6/B5/N5', 'teacher': 'SM/SZ/RE'},
            '7': {'subject': 'mittag', 'room': '', 'teacher': ''},
            '8': {'subject': 'qhu6', 'room': 'N7', 'teacher': ''},
            '9': {'subject': 'ffmd-gta', 'room': 'N7', 'teacher': ''}
        },
        'Mittwoch': {
            '1': {'subject': 'g', 'room': 'N7', 'teacher': 'EG'},
            '2': {'subject': 'l/f', 'room': 'E01/N7', 'teacher': 'WS/GT'},
            '3': {'subject': 'd', 'room': 'N7', 'teacher': 'KK'},
            '4': {'subject': 'm', 'room': 'N7', 'teacher': 'EF'},
            '5': {'subject': 'm', 'room': 'N7', 'teacher': 'EF'},
            '6': {'subject': 'fint/fint/lint', 'room': 'E06/N7/E01', 'teacher': ''},
            '7': {'subject': 'mittag', 'room': '', 'teacher': ''},
            '8': {'subject': 'qhu6', 'room': 'N7', 'teacher': ''},
            '9': {'subject': 'ffme-gta', 'room': 'N7', 'teacher': ''}
        },
        'Donnerstag': {
            '1': {'subject': 'f/l', 'room': 'N7/E01', 'teacher': 'GT/WS'},
            '2': {'subject': 'f/l', 'room': 'N7/E01', 'teacher': 'GT/WS'},
            '3': {'subject': 'ntbio', 'room': 'C15', 'teacher': 'HP'},
            '4': {'subject': 'mint/mint', 'room': 'A103/N7', 'teacher': ''},
            '5': {'subject': 'ntinf', 'room': 'E07', 'teacher': 'EG'},
            '6': {'subject': 'mittag', 'room': '', 'teacher': ''},
            '7': {'subject': 'sm/sw', 'room': 'TH2/TH4', 'teacher': 'HM/MR'},
            '8': {'subject': 'm', 'room': 'N7', 'teacher': 'EF'},
            '9': {'subject': 'e', 'room': 'N7', 'teacher': 'NL'}
        },
        'Freitag': {
            '1': {'subject': 'e', 'room': 'N7', 'teacher': 'NL'},
            '2': {'subject': 'e', 'room': 'N7', 'teacher': 'NL'},
            '3': {'subject': 'mu', 'room': 'A307', 'teacher': 'LG'},
            '4': {'subject': 'mu', 'room': 'A307', 'teacher': 'LG'},
            '5': {'subject': 'd', 'room': 'N7', 'teacher': 'KK'},
            '6': {'subject': 'd', 'room': 'N7', 'teacher': 'KK'},
            '7': {'subject': 'qhu', 'room': 'N4', 'teacher': ''},
            '8': {'subject': 'qhu', 'room': 'N4', 'teacher': ''}
        }
    },
    '6e': {
        'Montag': {
            '1': {'subject': 'd', 'room': 'N8', 'teacher': 'ZR'},
            '2': {'subject': 'e', 'room': 'N8', 'teacher': 'TS'},
            '3': {'subject': 'sm/sw/sw/sm', 'room': 'TH1/TH4/TH3/TH2', 'teacher': ''},
            '4': {'subject': 'sw/sm/sw/sm', 'room': 'TH3/TH2/TH4/TH1', 'teacher': ''},
            '5': {'subject': 'm', 'room': 'N8', 'teacher': 'SH'},
            '6': {'subject': 'mint/mint', 'room': 'N8/A108', 'teacher': ''},
            '7': {'subject': 'mittag', 'room': '', 'teacher': ''},
            '8': {'subject': 'qhu6', 'room': 'N8', 'teacher': ''},
            '9': {'subject': 'ffmd-gta', 'room': 'N8', 'teacher': ''}
        },
        'Dienstag': {
            '1': {'subject': 'mu', 'room': 'A301', 'teacher': 'KL'},
            '2': {'subject': 'l/f', 'room': 'N2/N8', 'teacher': 'TA/RN'},
            '3': {'subject': 'l/f', 'room': 'N2/N8', 'teacher': 'TA/RN'},
            '4': {'subject': 'm', 'room': 'N8', 'teacher': 'SH'},
            '5': {'subject': 'g', 'room': 'N8', 'teacher': 'BL'},
            '6': {'subject': 'g', 'room': 'N8', 'teacher': 'BL'},
            '7': {'subject': 'mittag', 'room': '', 'teacher': ''},
            '8': {'subject': 'qhu6', 'room': 'N8', 'teacher': ''},
            '9': {'subject': 'ffme-gta', 'room': 'N8', 'teacher': ''}
        },
        'Mittwoch': {
            '1': {'subject': 'mu', 'room': 'A307', 'teacher': 'KL'},
            '2': {'subject': 'ku', 'room': 'B104', 'teacher': 'GF'},
            '3': {'subject': 'ku', 'room': 'B104', 'teacher': 'GF'},
            '4': {'subject': 'd', 'room': 'N8', 'teacher': 'ZR'},
            '5': {'subject': 'lint/fint/fint', 'room': 'A101/N8/A204', 'teacher': ''},
            '6': {'subject': 'l/f', 'room': 'A101/N8', 'teacher': 'TA/RN'},
            '7': {'subject': 'mittag', 'room': '', 'teacher': ''},
            '8': {'subject': 'qhu6', 'room': 'N8', 'teacher': ''},
            '9': {'subject': 'ffmm-gta', 'room': 'N8', 'teacher': ''}
        },
        'Donnerstag': {
            '1': {'subject': 'd', 'room': 'N8', 'teacher': 'ZR'},
            '2': {'subject': 'f/l', 'room': 'N8/N2', 'teacher': 'RN/TA'},
            '3': {'subject': 'eth/k/ev', 'room': 'A104/N4/N8', 'teacher': 'AR/DG/SM'},
            '4': {'subject': 'ev/k/eth', 'room': 'N8/N4/A104', 'teacher': 'SM/DG/AR'},
            '5': {'subject': 'e', 'room': 'N8', 'teacher': 'TS'},
            '6': {'subject': 'mittag', 'room': '', 'teacher': ''},
            '7': {'subject': 'sm/sm/sw/sw', 'room': 'TH2/TH1/TH4/TH3', 'teacher': ''},
            '8': {'subject': 'ntbio', 'room': 'A15', 'teacher': 'SK'},
            '9': {'subject': 'ntbio', 'room': 'A15', 'teacher': 'SK'}
        },
        'Freitag': {
            '1': {'subject': 'e', 'room': 'N8', 'teacher': 'TS'},
            '2': {'subject': 'e', 'room': 'N8', 'teacher': 'TS'},
            '3': {'subject': 'm', 'room': 'N8', 'teacher': 'SH'},
            '4': {'subject': 'm', 'room': 'N8', 'teacher': 'SH'},
            '5': {'subject': 'd', 'room': 'N8', 'teacher': 'ZR'},
            '6': {'subject': 'ntinf', 'room': 'B101', 'teacher': 'SK'},
            '7': {'subject': 'qhu', 'room': 'N4', 'teacher': ''},
            '8': {'subject': 'qhu', 'room': 'N4', 'teacher': ''}
        }
    }
}

def fetch_dsb_data(username, password):
    """Obtener datos JSON directamente de la API de DSBmobile usando el endpoint correcto"""
    try:
        # Primero obtener el authid (token de autenticación)
        auth_url = f"https://mobileapi.dsbcontrol.de/authid?user={username}&password={password}&bundleid=de.heinekingmedia.dsbmobile&appversion=35&osversion=22&pushid="
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json'
        }
        
        # Obtener token de autenticación
        auth_response = requests.get(auth_url, headers=headers, timeout=15, verify=False)
        auth_response.raise_for_status()
        auth_id = auth_response.text.strip('"')
        
        if not auth_id or len(auth_id) < 10:
            print(f"Error de autenticación: {auth_response.text}")
            return None, None
            
        #print(f"Token de autenticación obtenido: {auth_id[:10]}...")
        
        # Obtener datos de horarios usando el token
        timetables_url = f"https://mobileapi.dsbcontrol.de/dsbtimetables?authid={auth_id}"
        
        response = requests.get(timetables_url, headers=headers, timeout=15, verify=False)
        response.raise_for_status()
        
        # Guardar datos originales para debug
        with open("debug/json_response.json", "w", encoding="utf-8") as f:
            json.dump(response.json(), f, ensure_ascii=False, indent=2)
        
        # Crear una sesión para solicitudes posteriores
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br'
        })
        session.verify = False
        
        return response.json(), session
    except Exception as e:
        print(f"Error obteniendo datos: {e}")
        return None, None

def is_target_class(class_text, target_classes):
    """Verificar si el texto contiene una clase objetivo con múltiples formatos"""
    if not class_text:
        return False
        
    # Limpiar el texto
    class_text = class_text.strip()
    
    # Verificar coincidencia directa
    if class_text in target_classes:
        return True
    
    # Verificar si es parte de una lista de clases
    for target in target_classes:
        # Patrones posibles: "6d", "6d,", ", 6d", "6d ", " 6d " etc.
        patterns = [
            f"^{target}$",             # Exacto: "6d"
            f"^{target},",             # Al inicio: "6d, algo"
            f", {target}$",            # Al final: "algo, 6d"
            f", {target},",            # En medio: "algo, 6d, algo"
            f"^{target} ",             # Al inicio con espacio: "6d algo"
            f" {target}$",             # Al final con espacio: "algo 6d"
        ]
        
        for pattern in patterns:
            if re.search(pattern, class_text):
                return True
    
    return False



def extract_date_from_title(soup):
    """Extraer la fecha del título sin los paréntesis"""
    title_elem = soup.find('div', class_='mon_title')
    if not title_elem:
        return "Fecha desconocida"
        
    full_text = title_elem.text.strip()
    # Eliminar el texto entre paréntesis
    date_text = re.sub(r'\s*\(.*?\)\s*', '', full_text)
    return date_text.strip()

def extract_day_of_week(date_str):
    """Extraer el día de la semana a partir de la fecha"""
    # Intentar extraer el día de la semana al final de la fecha
    day_match = re.search(r'(\w+)$', date_str)
    if day_match:
        day = day_match.group(1)
        days_mapping = {
            'Montag': 'Montag',
            'Dienstag': 'Dienstag',
            'Mittwoch': 'Mittwoch',
            'Donnerstag': 'Donnerstag',
            'Freitag': 'Freitag',
            'Samstag': 'Samstag',
            'Sonntag': 'Sonntag',
            'Monday': 'Montag',
            'Tuesday': 'Dienstag',
            'Wednesday': 'Mittwoch',
            'Thursday': 'Donnerstag',
            'Friday': 'Freitag',
            'Saturday': 'Samstag',
            'Sunday': 'Sonntag'
        }
        return days_mapping.get(day, "Desconocido")
    return "Desconocido"

def enhance_entry_with_schedule_info(entry, class_name):
    """Mejorar la entrada con información del horario regular"""
    short_class = class_name.lower()
    day_of_week = extract_day_of_week(entry.get('date', ''))
    period = entry.get('period', '')
    
    if short_class in CLASS_SCHEDULES and day_of_week in CLASS_SCHEDULES[short_class] and period in CLASS_SCHEDULES[short_class][day_of_week]:
        # Obtener información del horario regular
        schedule_info = CLASS_SCHEDULES[short_class][day_of_week][period]
        
        # Si no hay materia en la entrada de sustitución, usar la del horario
        if not entry.get('subject'):
            entry['subject'] = schedule_info.get('subject', '')
        
        # Guardar información adicional del horario
        entry['regular_subject'] = schedule_info.get('subject', '')
        entry['regular_room'] = schedule_info.get('room', '')
        entry['regular_teacher_code'] = schedule_info.get('teacher', '')
        
        # Convertir códigos de profesores a nombres completos si están disponibles
        teacher_codes = schedule_info.get('teacher', '').split('/')
        teacher_names = []
        for code in teacher_codes:
            if code and code in ALL_TEACHERS:
                teacher_names.append(f"{ALL_TEACHERS[code][0]} ({ALL_TEACHERS[code][1]})")
            elif code:
                teacher_names.append(code)
        
        if teacher_names:
            entry['regular_teacher'] = '/'.join(teacher_names)
    
    return entry

def enhance_entry_details(entry):
    """Mejorar detalles de la entrada con nombres completos de materias y profesores"""
    # Si no hay materia pero hay profesor original conocido, intentar inferir materia
    if not entry.get('subject') and entry.get('original_teacher') in ALL_TEACHERS:
        inferred_subject = ALL_TEACHERS[entry['original_teacher']][1].lower()
        entry['subject'] = inferred_subject

    # Si aún no hay materia, usar la del horario regular si existe
    if not entry.get('subject') and entry.get('regular_subject'):
        entry['subject'] = entry['regular_subject']

    # Mapear materia a nombre completo
    subject_code = entry.get('subject', '').lower()
    if subject_code in SUBJECT_MAPPING:
        entry['subject_full'] = SUBJECT_MAPPING[subject_code]
    else:
        entry['subject_full'] = subject_code if subject_code else "Sin materia"

    # Mapear materia regular a nombre completo
    regular_subject = entry.get('regular_subject', '').lower()
    if regular_subject in SUBJECT_MAPPING:
        entry['regular_subject_full'] = SUBJECT_MAPPING[regular_subject]
    else:
        entry['regular_subject_full'] = f"{regular_subject} (Desconocida)"

    # Mapear profesor original a nombre completo
    teacher_code = entry.get('original_teacher', '')
    if teacher_code in ALL_TEACHERS:
        entry['original_teacher_full'] = f"{ALL_TEACHERS[teacher_code][0]} ({ALL_TEACHERS[teacher_code][1]})"
    elif teacher_code:
        entry['original_teacher_full'] = f"{teacher_code} (Desconocido)"
    else:
        entry['original_teacher_full'] = ''

    # Mapear profesor sustituto a nombre completo
    substitute_code = entry.get('substitute', '')
    if substitute_code in ALL_TEACHERS:
        entry['substitute_full'] = f"{ALL_TEACHERS[substitute_code][0]} ({ALL_TEACHERS[substitute_code][1]})"
    elif substitute_code:
        entry['substitute_full'] = f"{substitute_code} (Desconocido)"
    else:
        entry['substitute_full'] = ''

    return entry

def extract_class_info(soup, target_classes):
    """Extraer información de clases usando múltiples métodos y fallback por texto plano"""
    all_entries = []

    for table in soup.find_all('table', class_='mon_list'):
        for row in table.find_all('tr'):
            cells = row.find_all('td', class_='list')
            if len(cells) >= 6:
                class_name = cells[0].text.strip()
                if any(tc in class_name for tc in target_classes):
                    # Extraer texto, aunque esté dentro de <strike>
                    original_cell = cells[3]
                    strike = original_cell.find('strike')
                    if strike:
                        original_teacher = strike.text.strip() if strike.text.strip() else original_cell.get_text(strip=True)
                    else:
                        original_teacher = original_cell.text.strip()

                    entry = {
                        "class": class_name,
                        "period": cells[1].text.strip(),
                        "substitute": cells[2].text.strip(),
                        "original_teacher": original_teacher,
                        "subject": cells[4].text.strip(),
                        "room": cells[5].text.strip(),
                        "notes": cells[6].text.strip() if len(cells) > 6 else ""
                    }
                    for cls in class_name.split(','):
                        entry_copy = entry.copy()
                        entry_copy['class'] = cls.strip()
                        entry_copy = enhance_entry_details(entry_copy)
                        all_entries.append(entry_copy)
                        #print("[DEBUG entry]:", entry_copy)
            else:
                raw_text = row.text.strip().replace('\xa0', ' ').replace('\u00a0', ' ').replace('\t', ' ')
                raw_text = re.sub(r'\s+', '', raw_text)
                if any(tc in raw_text for tc in target_classes):
                    #print("[DEBUG fallback]:", raw_text)
                    fallback_match = re.match(r'^(6[de])(\d)([A-Z]{2,4})([A-Z]{2,4})(E\d{2})$', raw_text)
                    if fallback_match:
                        class_name, period, substitute, original_teacher, room = fallback_match.groups()
                        entry = {
                            "class": class_name,
                            "period": period,
                            "substitute": substitute,
                            "original_teacher": original_teacher,
                            "subject": "",  # se intenta inferir luego
                            "room": room,
                            "notes": ""
                        }
                        all_entries.append(entry)

    return all_entries



def extract_timetable_info(json_data, session, target_classes):
    """Extraer información de horarios desde los datos JSON anidados"""
    if not json_data:
        return {}
    
    all_results = {}
    plan_urls = []
    
    try:
        # Procesar la estructura anidada para encontrar todas las URLs
        for timetable_group in json_data:
            group_title = timetable_group.get('Title', 'Sin título')
            group_date = timetable_group.get('Date', 'Fecha desconocida')
            
            # Si hay hijos, procesarlos
            if 'Childs' in timetable_group and timetable_group['Childs']:
                for child in timetable_group['Childs']:
                    # Extraer URL del plan
                    detail_url = child.get('Detail', '')
                    child_title = child.get('Title', 'Sin título')
                    child_date = child.get('Date', 'Fecha desconocida')
                    
                    # Construir un título compuesto
                    full_title = f"{group_title} - {child_title}"
                    
                    if detail_url and detail_url.startswith('http'):
                        plan_urls.append((detail_url, full_title, child_date))
        
        #print(f"Se encontraron {len(plan_urls)} URLs de planes")
        
        # Procesar cada URL encontrada
        for url, title, date in plan_urls:
            plan_key = f"{title} - {date}"
            #print(f"\nProcesando plan: {plan_key}")
            #print(f"URL: {url}")
            
            # Resultados para este plan
            plan_results = {}
            
            try:
                # Obtener el contenido HTML con los encabezados correctos
                response = session.get(url, timeout=15)
                
                # Verificar la respuesta
                if "406 - Client browser does not accept the MIME type" in response.text:
                    print("Error 406: Tipo MIME no aceptado")
                    # Intentar con diferentes encabezados Accept
                    session.headers.update({'Accept': '*/*'})
                    response = session.get(url, timeout=15)
                
                html_content = response.text
                
                # Guardar HTML para inspección (debug)
                debug_filename = f"debug/html_{title.replace(' ', '_').replace(':', '_')}.html"
                with open(debug_filename, "w", encoding="utf-8") as f:
                    f.write(html_content)
                
                # Verificar si sigue siendo un error 406
                if "406 - Client browser does not accept the MIME type" in html_content:
                    print("Error persistente 406. El servidor no acepta nuestros encabezados.")
                    continue
                
                # Analizar el HTML
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Extraer la fecha del título (sin paréntesis)
                date_str = extract_date_from_title(soup)
                #print(f"Fecha del título: {date_str}")
                
                # Método de análisis más robusto
                entries = extract_class_info(soup, target_classes)
                
                # Mejorar entradas con información de horarios
                for entry in entries:
                    class_name = entry['class']
                    # Añadir fecha y URL
                    entry['date'] = date_str
                    entry['url'] = url
                    
                    # Añadir día de la semana
                    entry['day_of_week'] = extract_day_of_week(date_str)
                    
                    # Normalizar clase (6d, 6e, etc.)
                    normalized_class = class_name.lower()
                    if len(normalized_class) > 2 and normalized_class[:2] in ['6d', '6e']:
                        normalized_class = normalized_class[:2]
                    
                    # Mejorar con información del horario regular
                    entry = enhance_entry_with_schedule_info(entry, normalized_class)
                    
                    # Mejorar con nombres completos de materias y profesores
                    entry = enhance_entry_details(entry)
                    
                    # Guardar en resultados
                    if class_name not in plan_results:
                        plan_results[class_name] = []
                    plan_results[class_name].append(entry)
                
                # Imprimir resumen
                found_classes = list(plan_results.keys())
                if found_classes:
                    #print(f"Clases encontradas: {', '.join(found_classes)}")
                    #print(f"Total de entradas: {sum(len(entries) for entries in plan_results.values())}")
                    print()
                else:
                    # No imprimir nada si no se encuentran clases para mantener la salida limpia
                    pass
                
            except Exception as url_error:
                print(f"Error procesando URL {url}: {url_error}")
            
            # Guardar los resultados
            if plan_results:
                # Usar la fecha del título como clave para el resultado
                all_results[date_str] = plan_results
            
        return all_results
        
    except Exception as e:
        print(f"Error extrayendo información de horarios: {e}")
        import traceback
        traceback.print_exc()
        return all_results

def format_results(results, target_classes):
    """Formatear y filtrar resultados para clases objetivo"""
    formatted = {}
    
    for date_str, class_info in results.items():
        #print(f"Processing date: {date_str}")
        # Agrupar por clase objetivo
        target_entries = {}
        for cls, entries in class_info.items():
            # Detectar si la clase es una de las objetivo
            is_target = False
            for target in target_classes:
                if is_target_class(cls, [target]):
                    is_target = True
                    if target not in target_entries:
                        target_entries[target] = []
                    #print(f"Adding {len(entries)} entries for class {target} on {date_str}")
                    #for entry in entries:
                        #print(f"  Entry: Period {entry.get('period')}, Subject {entry.get('subject')}")
                    target_entries[target].extend(entries)
        
        # Eliminar duplicados
        for class_name in target_entries:
            #print(f"Before deduplication: {len(target_entries[class_name])} entries for {class_name}")
            unique = []
            seen = set()
            for entry in target_entries[class_name]:
                key = (entry.get('period', ''), 
                       entry.get('subject', ''), 
                       entry.get('room', ''), 
                       entry.get('original_teacher', ''), 
                       entry.get('substitute', ''),
                       entry.get('date', ''),
                       entry.get('notes', ''))
                #print(f"  Checking entry: Period {entry.get('period')}, Key: {key}")
                if key not in seen:
                    seen.add(key)
                    unique.append(entry)
                #else:
                    #print(f"  Duplicate found: Period {entry.get('period')}, Key: {key}")
            
            #print(f"After deduplication: {len(unique)} entries for {class_name}")
            target_entries[class_name] = unique
            
        if target_entries:
            formatted[date_str] = target_entries
    
    return formatted

def save_results(results, filename="dsb_results.json"):
    """Guardar resultados en JSON"""
    try:
        path = os.path.join("results", filename)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        #print(f"Resultados guardados en {path}")
        return path
    except Exception as e:
        print(f"Error guardando resultados: {e}")
        return None

def print_summary(results):
    """Imprimir resumen de resultados con formato claro y mejorado"""
    if not results:
        print("No se encontraron resultados")
        return
    
    print("\n----- RESULTADOS FINALES -----")
    
    # Ordenar por fecha
    for date_str, classes in sorted(results.items()):
        print(f"\n{date_str}:")
        for class_name in sorted(classes.keys()):
            entries = classes[class_name]
            print(f"  Clase {class_name}:")
            
            # Ordenar entradas por periodo
            sorted_entries = sorted(entries, key=lambda x: x.get('period', '0') if x.get('period', '0').isdigit() else '0')
            
            for entry in sorted_entries:
                period = entry.get('period', '')
                
                # Usar materia del horario regular si está disponible, sino usar la de la sustitución
                subject = entry.get('regular_subject_full', '') or entry.get('subject_full', '') or entry.get('subject', '')
                
                # Información de aulas
                regular_room = entry.get('regular_room', '')
                current_room = entry.get('room', '')
                room_info = current_room if current_room else regular_room
                
                # Información de profesores
                original_teacher = entry.get('original_teacher_full', '') or entry.get('original_teacher', '')
                substitute = entry.get('substitute_full', '') or entry.get('substitute', '')
                
                # Notas adicionales
                notes = entry.get('notes', '')
                
                # Construir la línea de salida con formato mejorado
                output = f"    Periodo {period}: {subject}, Aula {room_info}"
                
                if original_teacher and substitute:
                    output += f", {original_teacher} → {substitute}"
                elif original_teacher:
                    output += f", {original_teacher}"
                
                if notes:
                    output += f", {notes}"
                
                print(output)

def main():
    # Credenciales y configuración
    username = "173002"
    password = "vplan"
    
    # Lista ampliada de posibles formatos de clases para mayor compatibilidad
    target_classes = ["6d", "6 d", "6D", "6.d", "6.e", "6e", "6 e", "6E"]
    
    # 1. Obtener datos JSON
    json_data, session = fetch_dsb_data(username, password)
    if not json_data:
        print("No se pudieron obtener datos")
        return
    
    # 2. Extraer información
    raw_results = extract_timetable_info(json_data, session, target_classes)
    
    # 3. Formatear resultados
    formatted_results = format_results(raw_results, target_classes)
    
    # 4. Guardar resultados
    save_path = save_results(formatted_results)
    
    # 5. Mostrar resumen
    print_summary(formatted_results)
    
    if save_path:
        print(f"\nDetalles completos guardados en: {save_path}")

if __name__ == "__main__":
    main()