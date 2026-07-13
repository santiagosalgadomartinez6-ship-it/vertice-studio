(function () {
  const selectClase = document.getElementById("clase_id");
  const selectFecha = document.getElementById("fecha");

  if (!selectClase || !selectFecha) return;

  const formateador = new Intl.DateTimeFormat("es-MX", {
    weekday: "long",
    day: "numeric",
    month: "long",
  });

  function etiquetaFecha(isoFecha, lugares) {
    const [anio, mes, dia] = isoFecha.split("-").map(Number);
    const fecha = new Date(anio, mes - 1, dia);
    const texto = formateador.format(fecha);
    const capitalizada = texto.charAt(0).toUpperCase() + texto.slice(1);
    if (lugares <= 0) return `${capitalizada} — sin lugares`;
    return `${capitalizada} — ${lugares} lugar${lugares === 1 ? "" : "es"} disponible${lugares === 1 ? "" : "s"}`;
  }

  async function cargarFechas(claseId) {
    selectFecha.innerHTML = "<option value=\"\">Cargando fechas...</option>";
    selectFecha.disabled = true;

    if (!claseId) {
      selectFecha.innerHTML = "<option value=\"\">Primero elige una clase</option>";
      return;
    }

    try {
      const respuesta = await fetch(`/api/clases/${claseId}/fechas`);
      const datos = await respuesta.json();

      selectFecha.innerHTML = "";
      const opcionInicial = document.createElement("option");
      opcionInicial.value = "";
      opcionInicial.textContent = "Selecciona una fecha";
      opcionInicial.disabled = true;
      opcionInicial.selected = true;
      selectFecha.appendChild(opcionInicial);

      datos.fechas.forEach((f) => {
        const opcion = document.createElement("option");
        opcion.value = f.fecha;
        opcion.textContent = etiquetaFecha(f.fecha, f.lugares_disponibles);
        opcion.disabled = f.lugares_disponibles <= 0;
        selectFecha.appendChild(opcion);
      });

      selectFecha.disabled = false;
    } catch (error) {
      selectFecha.innerHTML = "<option value=\"\">No se pudieron cargar las fechas</option>";
    }
  }

  selectClase.addEventListener("change", () => cargarFechas(selectClase.value));

  if (selectClase.value) {
    cargarFechas(selectClase.value);
  }
})();
