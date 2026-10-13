/* =========================================================================
   Comparador de series: hasta cuatro a la vez, de cualquier página.

   - Precios (bolsa, materias primas, divisas, cripto, gasolina): se llevan
     a base 100 en el primer día del periodo, para ver quién ha subido más.
   - Tasas (bonos, vivienda, alquiler): ya son porcentajes; van en su
     propia gráfica, con su valor tal cual.

   El catálogo sale de ../datos/resumen.json y cada serie de
   ../datos/series/<id>.json (las genera la portada dos veces al día).
   La selección se guarda en la dirección (#s=ibex,oro&r=1a) para poder
   compartirla. Todo con nodos, sin innerHTML.
   ========================================================================= */
(function () {
  "use strict";

  var NS = "http://www.w3.org/2000/svg";
  var COLORES = ["#1F5E8C", "#C1752A", "#2E7D4F", "#A03A2E"];
  var RANGOS = [["1m", "1 mes", 31], ["6m", "6 meses", 183], ["1a", "1 año", 366], ["5a", "5 años", 1827], ["10a", "10 años", 3653], ["todo", "Todo", 0]];
  var MAX = 4;

  var catalogo = [], porId = {}, cache = {};
  var estado = { sel: ["ibex", "sp500", "oro"], rango: "1a" };

  function el(nombre, at) { var n = document.createElementNS(NS, nombre); for (var k in at) n.setAttribute(k, at[k]); return n; }
  function crear(etiqueta, clase, texto) { var n = document.createElement(etiqueta); if (clase) n.className = clase; if (texto != null) n.textContent = String(texto); return n; }
  function vaciar(n) { while (n.firstChild) n.removeChild(n.firstChild); }
  function numero(v, dec) { return new Intl.NumberFormat("es-ES", { minimumFractionDigits: dec, maximumFractionDigits: dec }).format(v); }
  function fechaCorta(ms) { return new Date(ms).toLocaleDateString("es-ES", { day: "numeric", month: "short", year: "numeric" }); }

  function leerHash() {
    var h = location.hash.replace(/^#/, ""), p = {};
    h.split("&").forEach(function (kv) { var i = kv.indexOf("="); if (i > 0) p[kv.slice(0, i)] = decodeURIComponent(kv.slice(i + 1)); });
    if (p.s) estado.sel = p.s.split(",").filter(function (id) { return porId[id]; }).slice(0, MAX);
    if (p.r && RANGOS.some(function (r) { return r[0] === p.r; })) estado.rango = p.r;
  }
  function escribirHash() {
    history.replaceState(null, "", "#s=" + estado.sel.join(",") + "&r=" + estado.rango);
  }

  function color(id) { var i = estado.sel.indexOf(id); return i < 0 ? null : COLORES[i % COLORES.length]; }

  function pintarSelector() {
    var cont = document.getElementById("cmp-series");
    vaciar(cont);
    var grupos = [];
    catalogo.forEach(function (s) { if (grupos.indexOf(s.grupo) < 0) grupos.push(s.grupo); });
    grupos.forEach(function (g) {
      var caja = crear("div", "cmp-grupo");
      caja.appendChild(crear("h3", null, g));
      var fila = crear("div", "cmp-chips");
      catalogo.filter(function (s) { return s.grupo === g; }).forEach(function (s) {
        var b = crear("button", "cmp-chip", s.nombre);
        b.type = "button";
        var c = color(s.id);
        b.setAttribute("aria-pressed", c ? "true" : "false");
        if (c) b.style.setProperty("--c", c);
        b.addEventListener("click", function () {
          var i = estado.sel.indexOf(s.id);
          if (i >= 0) estado.sel.splice(i, 1);
          else { if (estado.sel.length >= MAX) estado.sel.shift(); estado.sel.push(s.id); }
          escribirHash(); pintarSelector(); cargarYDibujar();
        });
        fila.appendChild(b);
      });
      caja.appendChild(fila);
      cont.appendChild(caja);
    });
    var rangos = document.getElementById("cmp-rangos");
    vaciar(rangos);
    RANGOS.forEach(function (r) {
      var b = crear("button", null, r[1]);
      b.type = "button";
      b.setAttribute("aria-pressed", r[0] === estado.rango ? "true" : "false");
      b.addEventListener("click", function () { estado.rango = r[0]; escribirHash(); pintarSelector(); dibujar(); });
      rangos.appendChild(b);
    });
  }

  function cargarYDibujar() {
    var faltan = estado.sel.filter(function (id) { return !cache[id]; });
    if (!faltan.length) { dibujar(); return; }
    Promise.all(faltan.map(function (id) {
      return fetch("../datos/series/" + id + ".json").then(function (r) { return r.json(); }).then(function (d) {
        cache[id] = d.puntos.map(function (p) { return { t: Date.parse(p[0] + "T12:00:00Z"), v: p[1] }; });
      }).catch(function () { cache[id] = []; });
    })).then(dibujar);
  }

  // puntos de una serie dentro del periodo (el primero, el último dato en o antes del inicio)
  function recorte(id, desde) {
    var pts = cache[id] || [];
    if (!desde) return pts;
    var dentro = [], previo = null;
    for (var i = 0; i < pts.length; i++) {
      if (pts[i].t < desde) previo = pts[i];
      else dentro.push(pts[i]);
    }
    return previo ? [{ t: desde, v: previo.v }].concat(dentro) : dentro;
  }

  function dibujar() {
    var cont = document.getElementById("cmp-graficas");
    vaciar(cont);
    if (!estado.sel.length) { cont.appendChild(crear("p", "cmp-vacio", "Elige una o varias series de arriba.")); return; }
    var r = RANGOS.filter(function (x) { return x[0] === estado.rango; })[0];
    var fin = 0;
    estado.sel.forEach(function (id) { var p = cache[id] || []; if (p.length) fin = Math.max(fin, p[p.length - 1].t); });
    var desde = r[2] ? fin - r[2] * 864e5 : 0;
    var precios = estado.sel.filter(function (id) { return porId[id].tipo === "precio"; });
    var tasas = estado.sel.filter(function (id) { return porId[id].tipo !== "precio"; });
    if (precios.length) grafica(cont, precios, desde, true);
    if (tasas.length) grafica(cont, tasas, desde, false);
    var enlace = document.getElementById("cmp-enlace");
    if (enlace) enlace.textContent = location.href;
  }

  function grafica(cont, ids, desde, base100) {
    var lineas = ids.map(function (id) {
      var pts = recorte(id, desde);
      if (base100 && pts.length) { var b = pts[0].v || 1; pts = pts.map(function (p) { return { t: p.t, v: p.v / b * 100, real: p.v }; }); }
      else pts = pts.map(function (p) { return { t: p.t, v: p.v, real: p.v }; });
      return { id: id, s: porId[id], pts: pts, c: color(id) };
    }).filter(function (l) { return l.pts.length > 0; });
    var caja = crear("div", "cmp-lienzo");
    caja.appendChild(crear("p", "cmp-titulo", base100 ? "Evolución, base 100 al empezar el periodo" : "Valor en %"));
    if (!lineas.length) { caja.appendChild(crear("p", "cmp-vacio", "No hay datos en este periodo.")); cont.appendChild(caja); return; }

    var t0 = Infinity, t1 = -Infinity, v0 = Infinity, v1 = -Infinity;
    lineas.forEach(function (l) { l.pts.forEach(function (p) { t0 = Math.min(t0, p.t); t1 = Math.max(t1, p.t); v0 = Math.min(v0, p.v); v1 = Math.max(v1, p.v); }); });
    if (base100) { v0 = Math.min(v0, 100); v1 = Math.max(v1, 100); }
    var marg = (v1 - v0) * 0.08 || 1; v0 -= marg; v1 += marg;
    if (t1 === t0) t1 = t0 + 864e5;
    var A = 360, AL = 220, MI = 40, MD = 10, MS = 10, MB = 24;
    var X = function (t) { return MI + (A - MI - MD) * (t - t0) / (t1 - t0); };
    var Y = function (v) { return MS + (AL - MS - MB) * (1 - (v - v0) / (v1 - v0)); };
    var svg = el("svg", { viewBox: "0 0 " + A + " " + AL, role: "img", "aria-label": "Comparación de " + lineas.map(function (l) { return l.s.nombre; }).join(", ") });
    for (var k = 0; k <= 4; k++) {
      var v = v0 + (v1 - v0) * k / 4, y = Y(v);
      svg.appendChild(el("line", { x1: MI, y1: y, x2: A - MD, y2: y, "class": "rejilla" }));
      var t = el("text", { x: MI - 5, y: y + 3.5, "text-anchor": "end", "class": "eje" });
      t.textContent = numero(v, v1 - v0 < 5 ? 1 : 0);
      svg.appendChild(t);
    }
    if (base100) svg.appendChild(el("line", { x1: MI, y1: Y(100), x2: A - MD, y2: Y(100), "class": "base" }));
    [[t0, "start"], [t1, "end"]].forEach(function (q) {
      var e = el("text", { x: X(q[0]), y: AL - 6, "text-anchor": q[1], "class": "eje" });
      e.textContent = fechaCorta(q[0]);
      svg.appendChild(e);
    });
    lineas.forEach(function (l) {
      svg.appendChild(el("polyline", { points: l.pts.map(function (p) { return X(p.t).toFixed(1) + "," + Y(p.v).toFixed(1); }).join(" "), fill: "none", stroke: l.c, "stroke-width": 2, "stroke-linejoin": "round" }));
      if (l.pts.length < 30) l.pts.forEach(function (p) { svg.appendChild(el("circle", { cx: X(p.t), cy: Y(p.v), r: 2.6, fill: l.c })); });
    });
    var guia = el("line", { y1: MS, y2: AL - MB, "class": "guia" });
    svg.appendChild(guia);
    var marcas = lineas.map(function (l) { var m = el("circle", { r: 3.5, fill: l.c, stroke: "#fff", "stroke-width": 1.5, opacity: 0 }); svg.appendChild(m); return m; });
    caja.appendChild(svg);

    var leyenda = crear("div", "cmp-leyenda");
    lineas.forEach(function (l) {
      var sp = crear("span");
      sp.style.setProperty("--c", l.c);
      sp.appendChild(crear("i"));
      sp.appendChild(document.createTextNode(l.s.nombre + " "));
      var ult = l.pts[l.pts.length - 1];
      sp.appendChild(crear("b", null, base100 ? (ult.v >= 100 ? "+" : "") + numero(ult.v - 100, 1) + " %" : numero(ult.v, 2) + " %"));
      leyenda.appendChild(sp);
    });
    caja.appendChild(leyenda);

    var globo = crear("div", "cmp-globo");
    globo.hidden = true;
    caja.appendChild(globo);
    function valorEn(l, tt) { var m = null; for (var i = 0; i < l.pts.length && l.pts[i].t <= tt; i++) m = l.pts[i]; return m; }
    function mover(ev) {
      var cj = svg.getBoundingClientRect(), fx = Math.max(0, Math.min(1, (ev.clientX - cj.left) / cj.width)), px = fx * A;
      if (px < MI) px = MI;
      var tt = t0 + (px - MI) / (A - MI - MD) * (t1 - t0);
      guia.setAttribute("x1", px); guia.setAttribute("x2", px); guia.style.opacity = 1;
      vaciar(globo);
      globo.appendChild(crear("b", null, fechaCorta(tt)));
      lineas.forEach(function (l, i) {
        var p = valorEn(l, tt);
        if (!p) { marcas[i].setAttribute("opacity", 0); return; }
        marcas[i].setAttribute("cx", X(p.t)); marcas[i].setAttribute("cy", Y(p.v)); marcas[i].setAttribute("opacity", 1);
        var txt = l.s.nombre + ": " + numero(p.real, l.s.dec) + (l.s.unidad.indexOf("%") === 0 ? " %" : " " + l.s.unidad) + (base100 ? " (" + (p.v >= 100 ? "+" : "") + numero(p.v - 100, 1) + " %)" : "");
        globo.appendChild(crear("span", null, txt));
      });
      globo.hidden = false;
      var izq = fx * cj.width - globo.offsetWidth / 2;
      globo.style.left = Math.max(4, Math.min(cj.width - globo.offsetWidth - 4, izq)) + "px";
    }
    var activo = false;
    svg.addEventListener("pointerdown", function (e) { activo = true; mover(e); });
    svg.addEventListener("pointermove", function (e) { if (e.pointerType === "mouse" || activo) mover(e); });
    function salir() { activo = false; guia.style.opacity = 0; globo.hidden = true; marcas.forEach(function (m) { m.setAttribute("opacity", 0); }); }
    svg.addEventListener("pointerup", salir);
    svg.addEventListener("pointercancel", salir);
    svg.addEventListener("pointerleave", function (e) { if (e.pointerType === "mouse") salir(); });
    cont.appendChild(caja);
  }

  fetch("../datos/resumen.json").then(function (r) { return r.json(); }).then(function (d) {
    catalogo = d.series || [];
    catalogo.forEach(function (s) { porId[s.id] = s; });
    estado.sel = estado.sel.filter(function (id) { return porId[id]; });
    leerHash();
    pintarSelector();
    cargarYDibujar();
  }).catch(function () {
    document.getElementById("cmp-graficas").appendChild(crear("p", "cmp-vacio", "No se han podido cargar las series. Prueba dentro de un rato."));
  });

  var copiar = document.getElementById("cmp-copiar");
  if (copiar) copiar.addEventListener("click", function () {
    var hecho = function () { copiar.textContent = "Enlace copiado"; setTimeout(function () { copiar.textContent = "Copiar enlace"; }, 2000); };
    if (navigator.clipboard) navigator.clipboard.writeText(location.href).then(hecho, function () {});
  });
})();
