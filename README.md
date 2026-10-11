# Open Chess

Prototipo de escritorio para gestionar campeonatos escolares de ajedrez por sistema suizo.

## Funciones incluidas

- Hasta 15 grupos o torneos activos, cada uno con nombre propio.
- Alta, edición y retirada de alumnos; centro y curso son opcionales.
- Emparejamientos automáticos por puntuación, evitando repetir rival y equilibrando colores.
- Descanso automático cuando hay un número impar de participantes.
- Registro rápido mediante tres botones de resultado; tras puntuar, se selecciona automáticamente la mesa siguiente.
- Botón **Dejar pendiente** para borrar un resultado introducido por error.
- Clasificación con desempates Buchholz y número de victorias.
- Listados PDF de participantes, emparejamientos y clasificación.
- Una única ventana principal con tres pestañas: Grupos, Emparejamientos y Clasificaciones.
- Copias de seguridad por grupo con extensión `.openchess` y restauración segura como grupo nuevo.
- Interfaz colorida de alto contraste, con paneles redondeados, profundidad visual y pestañas destacadas.
- Icono propio con un caballo de ajedrez para macOS y Windows.
- Colegio asociado a cada grupo; `CEIP Vista Alegre` aparece por defecto en pantalla, copias y PDF.
- Eliminación definitiva de grupos, alumnos, rondas y resultados, con confirmación previa.
- Base de datos SQLite local; los datos permanecen al cerrar la aplicación.

## Probar ahora

Requiere Python 3.10 o posterior.

```bash
python3 -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
python run.py
```

La base de datos se guarda en `%APPDATA%\OpenChess\open_chess.db` en Windows y en
`~/.open_chess/open_chess.db` en macOS/Linux.

## Flujo de uso

1. Crea un grupo desde la barra lateral.
2. Introduce los alumnos. El centro puede quedar vacío para torneos internos.
3. Pulsa **Generar siguiente ronda**.
4. Selecciona una mesa y pulsa **Ganan blancas**, **Tablas** o **Ganan negras**. La selección avanza a la mesa siguiente. Usa **Dejar pendiente** para borrar un resultado accidental.
5. Cuando todos los resultados estén completos, genera la ronda siguiente.
6. Consulta o exporta la clasificación en cualquier momento.

## Copias de seguridad

Selecciona un grupo y pulsa **Guardar copia** en la barra lateral. La copia contiene sus alumnos,
rondas, emparejamientos y resultados. Para recuperarla, pulsa **Restaurar** y elige el archivo
`.openchess`. La restauración crea un grupo nuevo y nunca sobrescribe el original.

Todo el trabajo permanece dentro de la ventana principal. **Grupos** reúne los grupos y alumnos;
**Emparejamientos** reúne rondas, mesas y resultados; y **Clasificaciones** muestra el orden del
grupo seleccionado. La creación y edición se realizan mediante formularios internos, sin ventanas flotantes.

## Crear el programa para Windows 10/11

En un equipo Windows, ejecuta `build_windows.bat`. El programa portable aparecerá en
`dist\OpenChess\OpenChess.exe`.

Para crear un instalador clásico:

1. Instala Inno Setup 6.
2. Abre `installer\OpenChess.iss`.
3. Pulsa **Compile**.
4. El instalador se generará en `dist\installer`.

## Crear la aplicación para macOS

En un Mac, abre Terminal dentro de la carpeta del proyecto y ejecuta:

```bash
chmod +x build_mac.sh
./build_mac.sh
```

El script crea `OpenChess.app`, un instalador PKG y una copia ZIP de la aplicación dentro
de una carpeta `dist-<versión>`. El PKG instala **OpenChess** directamente en **Aplicaciones**;
el ZIP permite descomprimir la aplicación y arrastrarla manualmente a esa carpeta.

Los recursos del icono están en `assets`: PNG original, `OpenChess.icns` para macOS y
`OpenChess.ico` para Windows. Los scripts de compilación los incorporan automáticamente.

La compilación debe hacerse en la arquitectura de destino. Una aplicación creada en un Mac Intel es
`x86_64`; para obtener una aplicación nativa para Apple Silicon hay que ejecutar el mismo script
en un Mac con procesador Apple.

## Pruebas

```bash
python -m unittest discover -s tests -v
```

## Reglas de esta versión

- Victoria: 1 punto; tablas: 0,5; derrota: 0; descanso: 1.
- Orden: puntos, Buchholz, victorias y nombre.
- El emparejamiento prioriza rivales con puntuación cercana y penaliza fuertemente las repeticiones.
- Como preferencia secundaria evita enfrentar alumnos del mismo centro.

Antes de usarlo en un campeonato oficial conviene decidir y documentar reglas como número de rondas,
desempates alternativos, emparejamientos acelerados, ausencias y corrección de resultados históricos.
## Importar alumnos desde Excel

En la sección **Grupos**, selecciona un grupo y pulsa **Importar Excel**. La primera hoja debe usar las tres primeras columnas en este orden:

- A1: `Alumno` (nombre y apellidos en la misma celda)
- B1: `Curso`
- C1: `Centro educativo`

Los alumnos se leen desde la fila 2. Se admiten archivos `.xlsx` y `.xls`. Si una fila contiene un error, no se importa ninguna para que el grupo no quede a medias.
