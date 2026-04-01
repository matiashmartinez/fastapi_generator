import io
import os
import zipfile
from typing import List, Optional, Any, Dict
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field
from jinja2 import Environment, FileSystemLoader, select_autoescape

# ------------------------------------------------------------
# Modelos Pydantic para validar la configuración
# ------------------------------------------------------------
class FieldModel(BaseModel):
    name: str
    type: str               # "string", "integer", "boolean", "datetime", "float"
    required: bool = False
    unique: bool = False
    primary_key: bool = False
    default: Optional[Any] = None
    max_length: Optional[int] = None

class ModelConfig(BaseModel):
    name: str
    table_name: Optional[str] = None
    fields: List[FieldModel] = []

class Relationship(BaseModel):
    from_model: str
    to_model: str
    type: str               # "one-to-many", "many-to-one", "many-to-many"
    back_populates: Optional[str] = None

class SecurityConfig(BaseModel):
    enabled: bool = False
    type: str = "jwt"       # jwt, oauth2
    jwt_secret_key: str = "change_this_in_production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30

class DatabaseConfig(BaseModel):
    engine: str = "sqlite"  # sqlite, postgresql, mysql
    name: str = "app.db"
    user: str = ""
    password: str = ""
    host: str = "localhost"
    port: Optional[int] = None
    use_async: bool = False

class ProjectConfig(BaseModel):
    project_name: str = "my_fastapi_project"
    description: str = "Generated FastAPI API"
    version: str = "1.0.0"
    python_version: str = "3.11"
    database: DatabaseConfig
    security: SecurityConfig
    models: List[ModelConfig]
    relationships: List[Relationship] = []
    include_crud_all: bool = True
    include_pagination: bool = True
    include_filtering: bool = False
    include_sorting: bool = False
    include_testing: bool = True
    include_docker: bool = True
    include_alembic: bool = True
    include_env_file: bool = True
    admin_email: Optional[str] = None

# ------------------------------------------------------------
# Mapeo de tipos
# ------------------------------------------------------------
TYPE_MAP_SQLALCHEMY = {
    "string": "String",
    "integer": "Integer",
    "boolean": "Boolean",
    "datetime": "DateTime",
    "float": "Float",
}
TYPE_MAP_PYDANTIC = {
    "string": "str",
    "integer": "int",
    "boolean": "bool",
    "datetime": "datetime",
    "float": "float",
}
TYPE_MAP_PYTHON = {
    "string": "str",
    "integer": "int",
    "boolean": "bool",
    "datetime": "datetime.datetime",
    "float": "float",
}

def ensure_primary_key(model: ModelConfig) -> ModelConfig:
    """Asegura que el modelo tenga una clave primaria."""
    has_primary = any(field.primary_key for field in model.fields)
    if not has_primary:
        # Buscar un campo llamado "id" y marcarlo como primary_key
        for field in model.fields:
            if field.name == "id":
                field.primary_key = True
                field.unique = True
                has_primary = True
                break
        if not has_primary:
            # Si no existe, agregar campo id
            id_field = FieldModel(
                name="id",
                type="integer",
                required=True,
                unique=True,
                primary_key=True,
                default=None
            )
            model.fields.insert(0, id_field)
    return model

def map_sqlalchemy_type(field_type: str) -> str:
    return TYPE_MAP_SQLALCHEMY.get(field_type, "String")

def map_pydantic_type(field_type: str) -> str:
    return TYPE_MAP_PYDANTIC.get(field_type, "str")

def map_python_type(field_type: str) -> str:
    return TYPE_MAP_PYTHON.get(field_type, "str")

# ------------------------------------------------------------
# Procesamiento de relaciones
# ------------------------------------------------------------
def process_relationships(models: List[ModelConfig], relationships: List[Relationship]) -> Dict[str, Any]:
    """
    Devuelve un diccionario por modelo con información de relaciones:
    - foreign_keys: lista de {field_name, related_model, back_populates}
    - relationships: lista de {name, related_model, back_populates, uselist}
    """
    model_names = {m.name for m in models}
    result = {m.name: {"foreign_keys": [], "relationships": []} for m in models}

    for rel in relationships:
        if rel.from_model not in model_names or rel.to_model not in model_names:
            continue
        if rel.type == "one-to-many":
            # En from_model: relationship (uselist=True)
            result[rel.from_model]["relationships"].append({
                "name": rel.to_model.lower() + "s" if not rel.back_populates else rel.back_populates,
                "related_model": rel.to_model,
                "back_populates": rel.from_model.lower(),
                "uselist": True,
            })
            # En to_model: foreign key
            result[rel.to_model]["foreign_keys"].append({
                "field_name": rel.from_model.lower() + "_id",
                "related_model": rel.from_model,
                "back_populates": rel.to_model.lower() + "s",
            })
        elif rel.type == "many-to-one":
            # Equivalente a one-to-many invertido
            result[rel.to_model]["relationships"].append({
                "name": rel.from_model.lower() + "s",
                "related_model": rel.from_model,
                "back_populates": rel.to_model.lower(),
                "uselist": True,
            })
            result[rel.from_model]["foreign_keys"].append({
                "field_name": rel.to_model.lower() + "_id",
                "related_model": rel.to_model,
                "back_populates": rel.from_model.lower() + "s",
            })
        # many-to-many se puede implementar más adelante
    return result

# ------------------------------------------------------------
# Construcción del contexto para las plantillas
# ------------------------------------------------------------
def build_context(config: ProjectConfig) -> Dict[str, Any]:
    # Asegurar clave primaria en todos los modelos
    for model in config.models:
        ensure_primary_key(model)
    
    # Procesar relaciones
    relation_info = process_relationships(config.models, config.relationships)

    # Construir lista de modelos enriquecida
    processed_models = []
    for model in config.models:
        fields_sqlalchemy = []
        fields_pydantic = []
        fields_required = []
        fields_update = []

        for field in model.fields:
            # SQLAlchemy field
            sa_type = map_sqlalchemy_type(field.type)
            sa_kwargs = []
            if field.primary_key:
                sa_kwargs.append("primary_key=True")
            if field.unique:
                sa_kwargs.append("unique=True")
            if field.required and field.default is None:
                sa_kwargs.append("nullable=False")
            elif not field.required and field.default is None:
                sa_kwargs.append("nullable=True")
            if field.default is not None:
                if isinstance(field.default, str):
                    sa_kwargs.append(f"default='{field.default}'")
                else:
                    sa_kwargs.append(f"default={field.default}")
            if field.max_length and field.type == "string":
                sa_kwargs.append(f"length={field.max_length}")

            # Pydantic field
            pd_type = map_pydantic_type(field.type)
            pd_default = "..."
            if not field.required:
                pd_default = repr(field.default) if field.default is not None else "None"

            fields_sqlalchemy.append({
                "name": field.name,
                "type": sa_type,
                "kwargs": ", ".join(sa_kwargs),
                "python_type": map_python_type(field.type),
            })
            fields_pydantic.append({
                "name": field.name,
                "type": pd_type,
                "default": pd_default,
            })
            if not field.primary_key:
                fields_required.append(field.name)
            fields_update.append(field.name)

        # Agregar info de relaciones
        fk_info = relation_info.get(model.name, {}).get("foreign_keys", [])
        rel_info = relation_info.get(model.name, {}).get("relationships", [])

        processed_models.append({
            "name": model.name,
            "table_name": model.table_name or model.name.lower(),
            "fields": fields_sqlalchemy,
            "fields_pydantic": fields_pydantic,
            "fields_required": fields_required,
            "fields_update": fields_update,
            "foreign_keys": fk_info,
            "relationships": rel_info,
        })

    # Construir string de conexión
    db_engine = config.database.engine
    if db_engine == "sqlite":
        db_url = f"sqlite:///{config.database.name}"
    else:
        user = config.database.user
        password = config.database.password
        host = config.database.host
        port = config.database.port
        name = config.database.name
        if port:
            db_url = f"{db_engine}://{user}:{password}@{host}:{port}/{name}"
        else:
            db_url = f"{db_engine}://{user}:{password}@{host}/{name}"

    return {
        "project_name": config.project_name,
        "description": config.description,
        "version": config.version,
        "python_version": config.python_version,
        "database": {
            "engine": db_engine,
            "url": db_url,
            "name": config.database.name,
            "user": config.database.user,
            "password": config.database.password,
            "host": config.database.host,
            "port": config.database.port,
            "use_async": config.database.use_async,
        },
        "security": config.security.dict(),
        "models": processed_models,
        "relationships": config.relationships,
        "features": {
            "pagination": config.include_pagination,
            "filtering": config.include_filtering,
            "sorting": config.include_sorting,
            "testing": config.include_testing,
            "docker": config.include_docker,
            "alembic": config.include_alembic,
            "env_file": config.include_env_file,
        },
        "admin_email": config.admin_email,
    }

# ------------------------------------------------------------
# Motor de renderizado genérico (para plantillas del proyecto)
# ------------------------------------------------------------
project_env = Environment(
    loader=FileSystemLoader("templates/project"),
    autoescape=select_autoescape(["html", "xml"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


"""Recorre todos los archivos .j2 y los escribe en el ZIP con la extensión correcta."""
def render_templates(context: Dict[str, Any], zip_file: zipfile.ZipFile):
    base_dir = "templates/project"
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith(".j2"):
                rel_path = os.path.relpath(os.path.join(root, file), base_dir).replace("\\", "/")
                try:
                    template = project_env.get_template(rel_path)
                    rendered = template.render(context)
                except Exception as e:
                    print(f"❌ Error en plantilla: {rel_path}")
                    print(f"   {e}")
                    raise
                output_path = rel_path[:-3]
                zip_file.writestr(output_path, rendered)
            else:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, base_dir).replace("\\", "/")
                with open(full_path, "rb") as f:
                    zip_file.writestr(rel_path, f.read())

# ------------------------------------------------------------
# Motor para la interfaz web (solo index.html)
# ------------------------------------------------------------
ui_env = Environment(loader=FileSystemLoader("templates"))

# ------------------------------------------------------------
# FastAPI app
# ------------------------------------------------------------
app = FastAPI(title="FastAPI Generator Assistant")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    template = ui_env.get_template("index.html")
    content = template.render(request=request)
    return HTMLResponse(content)

@app.post("/generate")
async def generate_api(config: ProjectConfig):
    try:
        context = build_context(config)
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            render_templates(context, zip_file)
        zip_buffer.seek(0)
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={config.project_name}.zip"}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))