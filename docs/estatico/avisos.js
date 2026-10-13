/* =========================================================================
   Avisos y «desde tu última visita», comunes a las once páginas.

   Cada página lo carga desde la portada (/proyecciones/estatico/avisos.js)
   y este lee /proyecciones/datos/resumen.json, que genera la portada con
   el último dato de todas las series. Como todas las páginas viven en el
   mismo dominio, comparten el almacenamiento del navegador: lo que viste
   en una página cuenta en las demás.

   - Avisos: los movimientos poco habituales de las series de esta página
     (se pueden cerrar; no vuelven a salir).
   - Desde tu última visita: cuánto ha cambiado cada serie desde la última
     vez que la viste, si han pasado unas horas.

   Todo se construye con nodos, sin innerHTML, como el motor de gráficas.
   ========================================================================= */
(function () {
  "use strict";

  var script = document.currentScript;
  var pagina = (script && script.dataset.pagina) || location.pathname.split("/")[1] || "";
  var esHoy = pagina === "hoy";
  var CLAVE_VISTO = "proyecciones-visto";
  var CLAVE_CERRADOS = "proyecciones-avisos-cerrados";
  var HORAS_MIN = 3;

  function leer(clave, def) {
    try { var v = JSON.parse(localStorage.getItem(clave)); return v || def; } catch (e) { return def; }
  }
  function guardar(clave, v) {
    try { localStorage.setItem(clave, JSON.stringify(v)); } catch (e) {}
  }
  function crear(etiqueta, clase, texto) {
    var n = document.createElement(etiqueta);
    if (clase) n.className = clase;
    if (texto != null) n.textContent = String(texto);
    return n;
  }
  function numero(v, dec) {
    return new Intl.NumberFormat("es-ES", { minimumFractionDigits: dec, maximumFractionDigits: dec }).format(v);
  }
  function hace(t) {
    var h = Math.round((Date.now() - t) / 36e5);
    if (h < 24) return "hace " + h + (h === 1 ? " hora" : " horas");
    var d = Math.round(h / 24);
    return d === 1 ? "ayer" : "hace " + d + " días";
  }

  function estilos() {
    if (document.getElementById("pv-estilos")) return;
    var css = [
      ".pv-caja{margin:1.25rem 0 0;padding:.875rem 1rem;border-radius:.75rem;background:#fff;border:1px solid var(--regla,#C4C4CD);}",
      ".pv-caja h2{margin:0 0 .375rem;font-size:1.125rem;}",
      ".pv-aviso{display:flex;gap:.625rem;align-items:flex-start;margin:1rem 0 0;padding:.75rem .875rem;border-radius:.75rem;background:#fff;border-left:4px solid #C1752A;}",
      ".pv-aviso.nivel-alto{border-left-color:var(--alerta,#B03A2E);}",
      ".pv-aviso.nivel-bajo{border-left-color:var(--acento-2,#7E93B8);}",
      ".pv-aviso p{margin:0;flex:1;font-size:.9375rem;}",
      ".pv-aviso b{display:block;font-size:.75rem;text-transform:uppercase;letter-spacing:.04em;color:var(--tinta-suave,#63636E);}",
      ".pv-cerrar{flex:none;border:0;background:none;font:inherit;font-size:1.25rem;line-height:1;color:var(--tinta-suave,#63636E);cursor:pointer;padding:0 .25rem;min-height:2rem;}",
      ".pv-lista{margin:0;padding:0;list-style:none;display:grid;gap:.25rem;}",
      ".pv-lista li{display:flex;justify-content:space-between;gap:.75rem;font-size:.9375rem;}",
      ".pv-lista .sube{color:#2E7D4F;font-weight:600;}",
      ".pv-lista .baja{color:var(--alerta,#B03A2E);font-weight:600;}",
      ".pv-pie{margin:.5rem 0 0;font-size:.75rem;color:var(--tinta-suave,#63636E);}",
      ".pv-pie a{color:inherit;}"
    ].join("");
    var s = document.createElement("style");
    s.id = "pv-estilos";
    s.textContent = css;
    document.head.appendChild(s);
  }

  // dónde va: debajo de la entradilla de la página (o en el hueco de Hoy)
  function sitio() {
    var hueco = document.getElementById("desde-visita");
    if (hueco) return { padre: hueco, antes: null };
    var main = document.querySelector("main") || document.body;
    var ancla = main.querySelector(".bajada") || main.querySelector("h1");
    return ancla ? { padre: ancla.parentNode, antes: ancla.nextSibling } : { padre: main, antes: main.firstChild };
  }
  function poner(nodo, lugar) { lugar.padre.insertBefore(nodo, lugar.antes); lugar.antes = nodo.nextSibling; }

  function cambioTexto(s, desde) {
    if (s.tipo === "precio") {
      if (!desde) return null;
      var p = (s.ultimo / desde - 1) * 100;
      return { v: p, t: (p > 0 ? "+" : "") + numero(p, Math.abs(p) < 10 ? 1 : 0) + " %" };
    }
    var d = s.ultimo - desde;
    return { v: d, t: (d > 0 ? "+" : "") + numero(d, 2) + " puntos" };
  }

  function pintar(datos) {
    estilos();
    var lugar = sitio();
    var series = (datos.series || []).filter(function (s) { return esHoy || s.pagina === pagina; });

    // avisos de esta página (en Hoy ya salen en la propia página)
    if (!esHoy) {
      var cerrados = leer(CLAVE_CERRADOS, []);
      (datos.avisos || []).filter(function (a) { return a.pagina === pagina && cerrados.indexOf(a.id) === -1; }).slice(0, 2).forEach(function (a) {
        var caja = crear("div", "pv-aviso nivel-" + a.nivel);
        caja.setAttribute("role", "status");
        var p = crear("p");
        p.appendChild(crear("b", null, "Aviso"));
        p.appendChild(document.createTextNode(a.texto));
        caja.appendChild(p);
        var x = crear("button", "pv-cerrar", "×");
        x.setAttribute("aria-label", "Cerrar aviso");
        x.addEventListener("click", function () {
          var c = leer(CLAVE_CERRADOS, []);
          c.push(a.id);
          guardar(CLAVE_CERRADOS, c.slice(-60));
          caja.remove();
        });
        caja.appendChild(x);
        poner(caja, lugar);
      });
    }

    // desde tu última visita
    var visto = leer(CLAVE_VISTO, {});
    var ahora = Date.now(), filas = [], masViejo = ahora;
    series.forEach(function (s) {
      var v = visto[s.id];
      if (v && v.f !== s.fecha && ahora - v.t >= HORAS_MIN * 36e5) {
        var c = cambioTexto(s, v.v);
        if (c && Math.abs(c.v) > 0.0001) { filas.push({ s: s, c: c }); masViejo = Math.min(masViejo, v.t); }
      }
    });
    if (filas.length) {
      filas.sort(function (a, b) { return Math.abs(b.c.v) - Math.abs(a.c.v); });
      var caja = crear("section", "pv-caja");
      caja.appendChild(crear("h2", null, "Desde tu última visita"));
      var ul = crear("ul", "pv-lista");
      filas.slice(0, esHoy ? 8 : 5).forEach(function (f) {
        var li = crear("li");
        li.appendChild(crear("span", null, f.s.nombre));
        li.appendChild(crear("span", f.c.v > 0 ? "sube" : "baja", f.c.t));
        ul.appendChild(li);
      });
      caja.appendChild(ul);
      var pie = crear("p", "pv-pie", "Tu última visita fue " + hace(masViejo) + ". ");
      if (!esHoy) {
        var a = crear("a", null, "Ver España en datos hoy");
        a.href = new URL("../hoy/", script.src).href;
        pie.appendChild(a);
      }
      caja.appendChild(pie);
      poner(caja, lugar);
    }

    // apunta lo que has visto (cada serie, con su último dato)
    series.forEach(function (s) {
      var v = visto[s.id];
      if (!v || v.f !== s.fecha || ahora - v.t >= HORAS_MIN * 36e5) visto[s.id] = { v: s.ultimo, f: s.fecha, t: ahora };
    });
    guardar(CLAVE_VISTO, visto);
  }

  try {
    var url = new URL("../datos/resumen.json", script.src);
    fetch(url.href, { cache: "no-cache" }).then(function (r) { return r.ok ? r.json() : null; }).then(function (d) { if (d) pintar(d); }).catch(function () {});
  } catch (e) {}
})();
