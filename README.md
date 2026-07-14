# 📚 SubstituteFinder

Herramienta para consultar sustituciones y cancelaciones de clases en el plan de sustituciones DSB (Digitales Schwarzes Brett).

## 🎯 Características

- ✅ Consulta automática del plan de sustituciones DSB
- 📅 Visualización agrupada por fecha
- 👥 Seguimiento de múltiples hijos/clases
- 🔄 Detección de sustituciones de profesores
- ❌ Identificación de clases canceladas
- 📱 Interfaz optimizada para móviles (Termux)
- 🏫 Mapeo completo de profesores y asignaturas

## 📋 Requisitos

- Python 3.7 o superior
- Acceso a internet
- Credenciales DSB de tu colegio

### Dependencias Python

```bash
beautifulsoup4
requests
urllib3
```

## 🚀 Instalación

### En PC/Mac/Linux

```bash
# Clonar el repositorio
git clone https://github.com/Lacomax/SubstituteFinder.git
cd SubstituteFinder

# Instalar dependencias
pip install beautifulsoup4 requests urllib3

# Ejecutar
python dsb_finder.py
```

### En Android (Termux)

```bash
# Instalar Termux desde F-Droid
# https://f-droid.org/en/packages/com.termux/

# Dentro de Termux:
pkg install python git
pip install beautifulsoup4 requests urllib3

# Clonar y ejecutar
git clone https://github.com/Lacomax/SubstituteFinder.git
cd SubstituteFinder
python dsb_finder.py
```

## ⚙️ Configuración

### 1. Archivo de configuración

Copia la plantilla y rellena tus datos:

```bash
cp config.example.json config.json
```

```json
{
  "credentials": {"username": "TU_USUARIO_DSB", "password": "TU_CONTRASEÑA_DSB"},
  "children": [
    {"name": "NombreHijo1", "class": "7d", "schedule": "data/7d.json",
     "excluded_subjects": ["Ethik", "Latein", "DaZ-plus7"]},
    {"name": "NombreHijo2", "class": "7e", "schedule": "data/7e.json",
     "excluded_subjects": []}
  ],
  "notify": {"method": "none", "topic": ""}
}
```

`config.json` está en `.gitignore`: tus credenciales no se suben a git. También puedes usar las variables de entorno `DSB_USERNAME` y `DSB_PASSWORD`, que tienen prioridad sobre el archivo. Las clases objetivo, los nombres mostrados y los horarios cargados se derivan todos de `children`.

#### Asignaturas excluidas (`excluded_subjects`)

En las franjas compartidas del horario (p. ej. religión `k/ev/eth`, o `DaZ-plus7/intf`) la clase se divide en grupos y el plan de sustituciones publica una fila por cada grupo, aunque tu hijo solo asista a uno. Con `excluded_subjects` (opcional, por hijo) esas filas se descartan por completo: no aparecen en consola, ni en `results/dsb_results.json`, ni generan notificaciones.

Cada término se compara sin distinguir mayúsculas contra el **código** de la asignatura del plan (`eth`, `l`, `daz-plus7`) y contra su **nombre completo** según `data/subject_mapping.json` (`Ethik`, `Latein`). La coincidencia es exacta, nunca por subcadena: `"l"` excluye Latein pero no toca `lint` (Latein Intensiv). El filtro actúa sobre la asignatura del plan, no sobre la franja del horario: excluir `DaZ-plus7` oculta "DaZ cancelada", pero una cancelación de `intf` (el otro grupo de la misma franja) se sigue mostrando.

### 2. Horarios de clase

Los horarios están en los archivos `data/7d.json` y `data/7e.json`.

Ejemplo de estructura:

```json
{
  "clase": "7d",
  "eventos": [
    {"dia": 1, "periodo": 1, "asignatura": "d", "aula": "A104"},
    {"dia": 1, "periodo": 2, "asignatura": "m", "aula": "A104"}
  ]
}
```

- `dia`: 1=Lunes, 2=Martes, 3=Miércoles, 4=Jueves, 5=Viernes
- `periodo`: Número de período/hora
- `asignatura`: Código de asignatura (ver `data/subject_mapping.json`)
- `aula`: Sala/aula

## 🔔 Notificaciones

El script compara cada ejecución con la anterior y, si hay cambios nuevos, puede enviarte una notificación al móvil. Se configura en el bloque `notify` de `config.json`:

- `{"method": "none"}` — sin notificaciones (por defecto)
- `{"method": "ntfy", "topic": "mi-topic-secreto"}` — envía a [ntfy.sh](https://ntfy.sh): instala la app ntfy en el móvil y suscríbete al mismo topic. Elige un nombre de topic difícil de adivinar; cualquiera que lo conozca puede leer los mensajes.
- `{"method": "termux"}` — notificación local de Android vía `termux-notification` (requiere la app Termux:API y `pkg install termux-api`)

### Ejecución programada

Para que funcione como un servicio que avisa solo, programa la ejecución:

**En Termux (Android):**

```bash
pkg install cronie termux-services
sv-enable crond
crontab -e
# cada 30 min en horario escolar, de lunes a viernes:
# */30 6-17 * * 1-5 cd ~/SubstituteFinder && python dsb_finder.py >/dev/null 2>&1
```

**En Windows (Programador de tareas):**

```powershell
schtasks /Create /SC HOURLY /TN "SubstituteFinder" /TR "cmd /c cd /d C:\ruta\a\SubstituteFinder && python dsb_finder.py"
```

## 📊 Formato de salida

El formato está pensado para el ancho de un móvil (Termux): `H3` = hora/período 3, sin listas de aulas en la cabecera, y en franjas compartidas se muestra la asignatura del grupo concreto (p. ej. `Kath. Religionslehre`, no la franja genérica `Religion`).

```
==========
📅 18.11.2025 Dienstag
==========

 📚 Diego (7d):
  🔄 H3 Mathematik
     Michelle Schmidt ->
     Sandra Canals (Mathematik)
  ❌ H7 Intensivierung Mathematik
     CANCELADA
     intm entfällt!

 📚 Mateo (7e):
  ❌ H5 Kath. Religionslehre
     CANCELADA
  🔄 H6 Kath. Religionslehre
     Cambio: en A203
```

### Símbolos

- 🔄 = Sustitución de profesor
- ❌ = Clase cancelada
- ✅ = Sin cambios
- 📅 = Fecha
- 📚 = Clase/Hijo

## 📁 Estructura del proyecto

```
SubstituteFinder/
├── dsb_finder.py            # Script principal
├── data/
│   ├── 7d.json              # Horario clase 7d
│   ├── 7e.json              # Horario clase 7e
│   ├── teacher_map.json     # Mapeo de códigos de profesores
│   └── subject_mapping.json # Mapeo de códigos de asignaturas
├── results/                 # Resultados guardados (ignorado en git)
├── debug/                   # Archivos de depuración (ignorado en git)
├── _archive/                # Versiones antiguas
└── README.md                # Este archivo
```

## 🔧 Personalización avanzada

### Agregar nuevos profesores

Edita `data/teacher_map.json`:

```json
{
  "AB": ["Nombre Profesor", "Asignatura"]
}
```

### Agregar nuevas asignaturas

Edita `data/subject_mapping.json`:

```json
{
  "m": "Mathematik",
  "d": "Deutsch"
}
```

### Cambiar año escolar

Para cambiar de 7.Klasse a 8.Klasse:

1. Crea `data/8d.json` y `data/8e.json` con los horarios nuevos
2. Actualiza `config.json`:
   ```json
   "children": [
     {"name": "NombreHijo1", "class": "8d", "schedule": "data/8d.json"},
     {"name": "NombreHijo2", "class": "8e", "schedule": "data/8e.json"}
   ]
   ```

No hay que tocar el código.

## 🐛 Solución de problemas

### Error: "ModuleNotFoundError"

```bash
pip install beautifulsoup4 requests urllib3
```

### Error: "Couldn't get data"

- Verifica las credenciales DSB
- Comprueba tu conexión a internet
- Verifica que el servidor DSB esté funcionando

### No aparecen cambios para una clase

- Verifica que la clase esté en `target_classes`
- Confirma que el horario JSON esté correcto
- Revisa que los códigos coincidan con los del servidor DSB

## 🤝 Contribuir

Las contribuciones son bienvenidas:

1. Fork del repositorio
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit de cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📝 Licencia

Este proyecto es de código abierto y está disponible para uso personal y educativo.

## 👨‍👩‍👧‍👦 Créditos

Desarrollado para facilitar el seguimiento de los cambios en el horario escolar de Diego y Mateo.

## 📞 Soporte

Si tienes problemas o sugerencias, abre un [issue](https://github.com/Lacomax/SubstituteFinder/issues) en GitHub.

---

**Nota**: Este script es para uso personal/familiar. Asegúrate de cumplir con las políticas de tu colegio respecto al uso de credenciales DSB.
