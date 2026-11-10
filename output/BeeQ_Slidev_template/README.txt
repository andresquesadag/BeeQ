BeeQ — Proyecto minimo para exportar PDF con Slidev

REQUISITO: instalar Node.js LTS desde https://nodejs.org/

En Windows 11, abre PowerShell en esta carpeta (donde esta package.json) y ejecuta:

  npm install
  npm run export:pdf

Resultado: slides-export.pdf, dentro de esta misma carpeta.

Si queres ver las diapositivas antes:
  npm run dev
  Abre http://localhost:3030

Incluye 39 diapositivas (20 principales + 19 de respaldo), sin notas del presentador.
Se conserva exactamente el contenido visual de la version BeeQ Slidev v6.
La carpeta public/ contiene solo las imagenes referenciadas por slides.md.
La carpeta styles/ define el diseno. No cambies las rutas relativas.

Si Windows PowerShell bloquea npm.ps1, utiliza npm.cmd:
  npm.cmd install
  npm.cmd run export:pdf

Si Chromium no se descarga durante npm install:
  npx playwright install chromium

Nota: los comandos de npm requieren internet en la primera instalacion.
