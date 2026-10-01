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
La contraseña del panel sale de la variable de entorno `VERTICE_PANEL_PASSWORD`; si no existe, el panel no deja entrar. Para probarlo en tu computadora, en PowerShell: `$env:VERTICE_PANEL_PASSWORD = "la-que-quieras"` antes de `python app.py`. En Render la genera el propio Render (ver `render.yaml`) y se consulta en **Environment**. Nunca la escribas en el código: el repositorio es público.

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
- Para producción: mover `VERTICE_SECRET_KEY` a una variable de entorno real (la contraseña del panel ya está en `VERTICE_PANEL_PASSWORD`) y correr con un servidor WSGI (gunicorn/waitress), no con `debug=True`.
