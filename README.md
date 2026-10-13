# Proyecciones

Once páginas de datos públicos, con gráficas interactivas, cada una en su
propio repositorio y su propio GitHub Pages gratuito. Esta es la portada
que enlaza a todas.

| Página | Repositorio | Qué muestra |
|---|---|---|
| [Bolsa](https://adrianezd.github.io/proyecciones-bolsa/) | [proyecciones-bolsa](https://github.com/adrianezd/proyecciones-bolsa) | S&P 500, Nasdaq, IBEX, Euro Stoxx, Nikkei |
| [Materias primas](https://adrianezd.github.io/proyecciones-materias-primas/) | [proyecciones-materias-primas](https://github.com/adrianezd/proyecciones-materias-primas) | Oro, plata, Brent, gas natural |
| [Divisas](https://adrianezd.github.io/proyecciones-divisas/) | [proyecciones-divisas](https://github.com/adrianezd/proyecciones-divisas) | Euro/dólar, euro/libra, euro/yen |
| [Bitcoin](https://adrianezd.github.io/proyecciones-bitcoin/) | [proyecciones-bitcoin](https://github.com/adrianezd/proyecciones-bitcoin) | Bitcoin, Ethereum, XRP |
| [Bonos](https://adrianezd.github.io/proyecciones-bonos/) | [proyecciones-bonos](https://github.com/adrianezd/proyecciones-bonos) | Deuda a 10 años, 8 países del euro |
| [Vivienda](https://adrianezd.github.io/proyecciones-vivienda/) | [proyecciones-vivienda](https://github.com/adrianezd/proyecciones-vivienda) | Proyección del precio de compra |
| [Alquiler](https://adrianezd.github.io/proyecciones-alquiler/) | [proyecciones-alquiler](https://github.com/adrianezd/proyecciones-alquiler) | Proyección de la renta mensual |
| [Gasolina](https://adrianezd.github.io/proyecciones-gasolina/) | [proyecciones-gasolina](https://github.com/adrianezd/proyecciones-gasolina) | Precio por provincia, 53 páginas |
| [Supermercado](https://adrianezd.github.io/proyecciones-supermercado/) | [proyecciones-supermercado](https://github.com/adrianezd/proyecciones-supermercado) | Precios de la compra en España |
| [Terremotos](https://adrianezd.github.io/proyecciones-terremotos/) | [proyecciones-terremotos](https://github.com/adrianezd/proyecciones-terremotos) | Sismos del mundo, últimas 24 h |
| [Sismos en España](https://adrianezd.github.io/proyecciones-sismos/) | [proyecciones-sismos](https://github.com/adrianezd/proyecciones-sismos) | Frecuencia histórica y periodos de retorno |

## Por qué repos separados

Cada página vive en su propio repositorio con su propia GitHub Action y
su propio GitHub Pages: si una fuente de datos falla o cambia, solo se ve
afectada esa página, no las demás. Cada repo trae su generador en
Python, su plantilla y su motor de gráficas (`estatico/grafica.js`, SVG
puro sin dependencias) para poder desplegarse de forma independiente.

## Ninguna cifra está inventada

Regla del proyecto, en las once páginas: si una fuente no responde y no
hay copia en caché, la página no se genera. Nunca se rellena un hueco con
datos aproximados o "de ejemplo".

## Hoy, comparador y avisos

Este repositorio es la portada y, además, junta las once páginas:

- **[España en datos hoy](https://adrianezd.github.io/proyecciones/hoy/)**: lo más llamativo del día, con el último dato y los cambios de cada serie.
- **[Comparar](https://adrianezd.github.io/proyecciones/comparar/)**: hasta cuatro series de cualquier página en la misma gráfica (precios en base 100, tasas con su valor). La selección va en la dirección para compartirla.
- **Avisos y «desde tu última visita»** en las once páginas: cada una carga `/proyecciones/estatico/avisos.js`, que lee `datos/resumen.json`.

`fuente/construir.py` (solo librería estándar) no consulta las fuentes originales: lee la caché que cada página guarda en su repo (`cache/*.json`) y escribe `docs/datos/` y `docs/hoy/`. La GitHub Action lo lanza media hora después de que se actualicen las páginas (06:40 y 18:40 UTC). Como la caché de gasolina solo tiene el día de hoy, el histórico de la media nacional se guarda aquí, en `historia/gasolina.json`.

Un aviso sale cuando un movimiento es poco habitual para esa serie (más de 2,5 desviaciones de su variación normal en un día o una semana), con máximos o mínimos de un año, con bonos que se mueven más de 0,35 puntos en un mes, gasolina que cambia 3 céntimos en una semana o terremotos fuertes.
