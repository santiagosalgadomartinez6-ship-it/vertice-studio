# Vértice Studio — Sistema de reservación de clases

Proyecto de portafolio (pieza freelance de demostración). **Vértice es una marca ficticia** creada para mostrar un sistema completo de reservaciones con backend real, como el que se vendería a un gimnasio, spa o consultorio.

Pensado como complemento de un sitio estático tipo landing page (ver proyecto `penumbra`): aquí la pieza clave es el **backend con Python + Flask + SQLite**, no solo el frontend.

## Qué incluye

- Landing page con horario semanal de clases (lee de base de datos)
- Formulario de reservación con selección de fecha dinámica vía API (AJAX/fetch)
- Control de cupo real: si una clase se llena, no se puede reservar
- Panel de administración con login (usuario/contraseña) para ver y cancelar reservaciones
- Base de datos SQLite que se crea sola al primer arranque, con datos de ejemplo

## Cómo correrlo

```
pip install -r requirements.txt
python app.py
```

Abre `http://127.0.0.1:5000/`.

El panel de administración está en `http://127.0.0.1:5000/admin/login`.
Contraseña de prueba: `vertice2026` (definida en `app.py`, cámbiala con la variable de entorno `VERTICE_ADMIN_PASSWORD` antes de usar esto con un cliente real).

## Estructura del proyecto

```
vertice/
├── app.py              (rutas Flask)
├── database.py         (acceso a SQLite, lógica de cupo y fechas)
├── requirements.txt
├── vertice.db          (se genera sola al arrancar)
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── reservar.html
│   ├── confirmacion.html
│   ├── admin_login.html
│   └── admin_dashboard.html
└── static/
    ├── css/style.css
    └── js/main.js
```

## Cómo adaptarlo a un cliente real

- Las clases y horarios semilla están en `database.py`, función `init_db()` — cámbialos por los del negocio real.
- Los datos de contacto (dirección, teléfono, redes) están hardcodeados en `templates/base.html`.
- Para producción: mover `VERTICE_SECRET_KEY` y `VERTICE_ADMIN_PASSWORD` a variables de entorno reales y correr con un servidor WSGI (gunicorn/waitress), no con `debug=True`.
