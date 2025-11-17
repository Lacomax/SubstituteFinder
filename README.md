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

### 1. Credenciales DSB

Edita `dsb_finder.py` y modifica las credenciales (línea 410):

```python
username, password = "TU_USUARIO", "TU_CONTRASEÑA"
```

### 2. Clases objetivo

Modifica las clases que quieres seguir (línea 411):

```python
target_classes = ["7d", "7D", "7.d", "7e", "7E", "7.e"]
```

### 3. Nombres de hijos

Personaliza los nombres en la función `print_summary` (líneas 337-340):

```python
class_to_child = {
    '7d': 'Diego',
    '7e': 'Mateo'
}
```

### 4. Horarios de clase

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

## 📊 Formato de salida

```
==========
📅 18.11.2025 Dienstag
==========

  📚 Diego (7d):
    🔄 Period 3: Mathematik (A104)
       Michelle Schmidt ->
       Sandra Canals (Mathematik)

    ❌ Period 7: Intensivierung Mathematik (A104)
       CANCELADA
       intm entfällt!

  📚 Mateo (7e): ✅ Sin cambios
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

1. Renombra o crea `data/8d.json` y `data/8e.json`
2. Modifica línea 17 en `dsb_finder.py`:
   ```python
   for class_file in ['data/8d.json', 'data/8e.json']:
   ```
3. Modifica línea 411:
   ```python
   target_classes = ["8d", "8D", "8.d", "8e", "8E", "8.e"]
   ```
4. Actualiza líneas 251, 337-340 con '8d' y '8e'

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
