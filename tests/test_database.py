"""Pruebas para database.py.

No usan vertice.db: cada prueba crea su propio archivo sqlite temporal y
sobrescribe database.DB_PATH antes de llamar a database.init_db(). Esto
funciona porque get_db() lee el nombre global DB_PATH en cada llamada
(no lo cachea en un closure), así que basta con reasignar el atributo del
módulo.

Ejecutar desde la carpeta del proyecto (vertice/):
    python -m unittest discover -s tests
"""

import os
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

# tests/ no es un paquete del proyecto: agregamos la carpeta raíz de
# vertice (el padre de tests/) a sys.path para poder hacer `import database`
# sin importar desde dónde se invoque unittest discover.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import database  # noqa: E402


class TestDatabase(unittest.TestCase):
    def setUp(self):
        self._db_path_original = database.DB_PATH

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        tmp.close()
        self.tmp_path = tmp.name

        database.DB_PATH = Path(self.tmp_path)
        database.init_db()

        clases = database.obtener_clases()
        self.clase = clases[0]
        self.clase_id = self.clase["id"]
        self.capacidad = self.clase["capacidad"]
        # Fecha lejana en el futuro para no chocar con datos sembrados.
        self.fecha = "2099-01-07"

    def tearDown(self):
        database.DB_PATH = self._db_path_original
        try:
            os.unlink(self.tmp_path)
        except OSError:
            pass

    # -- lugares_disponibles ------------------------------------------------

    def test_lugares_disponibles_capacidad_completa_antes_de_reservar(self):
        self.assertEqual(
            database.lugares_disponibles(self.clase_id, self.fecha), self.capacidad
        )

    def test_lugares_disponibles_decrece_por_cada_reservacion(self):
        database.crear_reservacion(self.clase_id, "Ana", "5511110000", "ana@correo.com", self.fecha)
        self.assertEqual(
            database.lugares_disponibles(self.clase_id, self.fecha), self.capacidad - 1
        )
        database.crear_reservacion(self.clase_id, "Beto", "5511110001", "beto@correo.com", self.fecha)
        self.assertEqual(
            database.lugares_disponibles(self.clase_id, self.fecha), self.capacidad - 2
        )

    def test_lugares_disponibles_nunca_baja_de_cero(self):
        for i in range(self.capacidad + 3):
            database.crear_reservacion(
                self.clase_id, f"Cliente {i}", "5511110000", f"cliente{i}@correo.com", self.fecha
            )
        self.assertEqual(database.lugares_disponibles(self.clase_id, self.fecha), 0)

    def test_lugares_disponibles_clase_inexistente_devuelve_cero(self):
        self.assertEqual(database.lugares_disponibles(999999, self.fecha), 0)

    # -- crear_reservacion / obtener_reservacion -----------------------------

    def test_crear_reservacion_devuelve_id_y_es_recuperable(self):
        reservacion_id = database.crear_reservacion(
            self.clase_id, "Carla Ruiz", "5511223344", "carla@correo.com", self.fecha
        )
        self.assertIsInstance(reservacion_id, int)

        reservacion = database.obtener_reservacion(reservacion_id)
        self.assertIsNotNone(reservacion)
        self.assertEqual(reservacion["nombre_cliente"], "Carla Ruiz")
        self.assertEqual(reservacion["telefono"], "5511223344")
        self.assertEqual(reservacion["email"], "carla@correo.com")
        self.assertEqual(reservacion["fecha"], self.fecha)
        self.assertEqual(reservacion["clase_id"], self.clase_id)
        self.assertEqual(reservacion["estado"], "confirmada")

    # -- proximas_fechas ------------------------------------------------------

    def test_proximas_fechas_cantidad_dia_y_espaciado(self):
        dia_semana = 2  # miércoles
        cantidad = 4
        fechas = database.proximas_fechas(dia_semana, cantidad=cantidad)

        self.assertEqual(len(fechas), cantidad)

        hoy = datetime.now().date()
        for fecha in fechas:
            self.assertEqual(fecha.weekday(), dia_semana)
            self.assertGreaterEqual(fecha, hoy)

        for anterior, siguiente in zip(fechas, fechas[1:]):
            self.assertEqual((siguiente - anterior).days, 7)

    # -- cancelar_reservacion ---------------------------------------------------

    def test_cancelar_reservacion_actualiza_estado_y_libera_lugar(self):
        reservacion_id = database.crear_reservacion(
            self.clase_id, "Diego", "5511110000", "diego@correo.com", self.fecha
        )
        self.assertEqual(
            database.lugares_disponibles(self.clase_id, self.fecha), self.capacidad - 1
        )

        database.cancelar_reservacion(reservacion_id)

        reservacion = database.obtener_reservacion(reservacion_id)
        self.assertEqual(reservacion["estado"], "cancelada")
        self.assertEqual(
            database.lugares_disponibles(self.clase_id, self.fecha), self.capacidad
        )


if __name__ == "__main__":
    unittest.main()
