Documentación: Generador de Proyectos FastAPI
📦 ¿Qué hace?
El asistente recibe la configuración a través de un formulario y genera un proyecto backend completo.

Recibe desde un formulario:

Nombre del proyecto y descripción.

Motor de base de datos (SQLite, PostgreSQL, MySQL).

Configuración de autenticación JWT (opcional).

Definición de modelos de negocio con sus campos (nombre, tipo, restricciones).

Relaciones entre modelos (uno a muchos, muchos a uno).

Opciones adicionales (paginación, filtros, tests, Docker, Alembic, etc.).

Procesamiento y Generación:

Procesa la configuración, valida y enriquece los modelos (por ejemplo, agrega id como clave primaria si falta).

Genera un proyecto FastAPI completo y estructurado, empaquetado en un archivo ZIP listo para descargar.

El proyecto generado incluye:

Modelos SQLAlchemy con relaciones.

Esquemas Pydantic para validación.

Operaciones CRUD reutilizables.

Endpoints REST automáticos para cada modelo.

Dependencias de autenticación (si se habilita).

Archivos de configuración, variables de entorno, Docker y migraciones.

⚙️ ¿Cómo funciona?
1. Backend (FastAPI)
Expone dos endpoints principales:

GET / : Muestra la interfaz web (index.html).

POST /generate : Recibe la configuración JSON, construye un contexto enriquecido y genera el archivo ZIP.

2. Procesamiento de la Configuración
Se validan los modelos utilizando Pydantic.

Se asegura que cada modelo tenga una clave primaria (agrega automáticamente un campo id si no existe).

Se mapean los tipos de campo del formulario a tipos de SQLAlchemy y Pydantic.

Se procesan las relaciones para generar correctamente los ForeignKey y relationship.

Se construye un diccionario context con toda la información necesaria para inyectar en las plantillas.

3. Generación de Archivos
Plantillas estáticas: Se recorren todos los archivos .j2 en templates/project/ (excepto la carpeta dynamic/) y se renderizan con el contexto. El resultado se escribe en el ZIP manteniendo la estructura de carpetas original.

Plantillas dinámicas: Por cada modelo definido, se toman las plantillas en templates/project/dynamic/ (_model.py.j2, _schema.py.j2, _crud.py.j2, _endpoint.py.j2) y se generan los archivos correspondientes con el nombre del modelo (ej. app/models/cliente.py).

Archivos adicionales: Se copian archivos que no son .j2 (como .gitignore o imágenes) si existieran.

4. Entrega
El archivo ZIP compilado se envía directamente al navegador del usuario para su descarga.

🧩 Tecnologías utilizadas
FastAPI: Backend del asistente.

Jinja2: Motor de plantillas para generar el código de los proyectos.

Pydantic: Validación estricta de la configuración ingresada.

Uvicorn: Servidor ASGI para ejecutar la aplicación.

HTML / CSS / JS: Interfaz web interactiva con campos dinámicos.

📁 Estructura del asistente
Plaintext
fastapi-generator/
├── main.py                      # Código principal del asistente
├── templates/
│   ├── index.html               # Formulario web principal
│   └── project/                 # Plantillas del proyecto generado
│       ├── app/                 # Estructura fija del proyecto
│       │   ├── main.py.j2
│       │   ├── core/
│       │   ├── db/
│       │   ├── models/          # (__init__.py.j2)
│       │   ├── schemas/         # (__init__.py.j2)
│       │   ├── crud/            # (base.py.j2, __init__.py.j2)
│       │   └── api/             # (deps.py.j2, api_v1/...)
│       ├── dynamic/             # Plantillas que se replican por modelo
│       │   ├── _model.py.j2
│       │   ├── _schema.py.j2
│       │   ├── _crud.py.j2
│       │   └── _endpoint.py.j2
│       ├── requirements.txt.j2
│       ├── .env.j2
│       └── README.md.j2
└── requirements.txt             # Dependencias del asistente
🚀 Requisitos para ejecutarlo
Tener instalado Python 3.11 o superior.

Instalar las dependencias necesarias. Ejecuta en tu terminal:

Bash
pip install fastapi uvicorn jinja2 pydantic python-multipart
Asegurarte de tener la estructura de carpetas y archivos de plantillas completa (tal como se describió en la sección anterior).

Ejecutar el servidor local:

Bash
uvicorn main:app --reload
Abrir http://localhost:8000 en el navegador web para usar la interfaz.
