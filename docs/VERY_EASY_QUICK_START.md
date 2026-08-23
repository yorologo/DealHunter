# ⚡ Very Very Easy Quick Start — Android

¿Nunca has usado Termux, Shizuku, Python o Git?

No importa.

Esta guía está diseñada para que tú sólo prepares Android y una IA de
programación. Después, la IA instala y configura DealHunter por ti.

---

## ¿Qué vamos a instalar?

### Termux

Termux convierte tu Android en un pequeño entorno Linux.

DealHunter se ejecutará dentro de Termux.

NO necesitas root.

### Shizuku

Shizuku permite que Termux pueda realizar determinadas acciones de Android
con permisos ADB sin root.

DealHunter lo utiliza, entre otras cosas, para integrarse con la aplicación
oficial de Rappi.

### Codex / Antigravity

Son agentes de programación capaces de trabajar directamente dentro de
Termux.

Sólo necesitas UNO.

Puedes instalar:

- Codex
- Google Antigravity
- o ambos

Después simplemente pegarás el prompt de instalación de DealHunter.

---

# PASO 1 — Instala Termux

Instálalo desde una fuente oficial.

Recomendado:

1. F-Droid
2. GitHub Releases oficial de Termux

NO mezcles Termux y sus plugins descargados desde fuentes diferentes.

Abre Termux una vez después de instalarlo.

[Descargar Termux desde F-Droid](https://f-droid.org/packages/com.termux/)

[Descargar Termux desde GitHub oficial](https://github.com/termux/termux-app/releases)

---

# PASO 2 — Instala Shizuku

Instala Shizuku desde su distribución oficial.

Después:

1. Abre Shizuku.
2. Sigue la guía para iniciarlo mediante Depuración inalámbrica (Android 11+).
3. Comprueba que Shizuku indique que está funcionando.
4. Autoriza Termux cuando Shizuku lo solicite.

En Shizuku busca:

Usar Shizuku en aplicaciones de terminal
→ Exportar archivos

Guárdalos en:

Downloads/shizuku

Deben aparecer:

rish
rish_shizuku.dex

No necesitas editar estos archivos manualmente.
La IA lo hará después.

[Descargar Shizuku](https://shizuku.rikka.app/download/)

---

# PASO 3 — Prepara Termux

Abre Termux y ejecuta:

```bash
pkg update && pkg upgrade -y
termux-setup-storage
```

Acepta el permiso de almacenamiento si Android lo solicita.

---

# PASO 4 — Instala una IA

Puedes escoger Codex, Antigravity o ambos. (Nota: Los ports para Termux son comunitarios y no son distribuciones oficiales de OpenAI o Google, pero funcionan de manera equivalente en este entorno).

## Opción A — Codex

Sigue la guía: [Instalación de Termux y AI](installation-termux.md) → sección Codex

Cuando termine:

```bash
codex login --device-auth
```

Completa el inicio de sesión en el navegador.

Comprueba:

```bash
codex login status
```

Después inicia:

```bash
codex
```

## Opción B — Antigravity

Sigue la guía: [Instalación de Termux y AI](installation-termux.md) → sección Antigravity

Comprueba:

```bash
agy --version
```

Después:

```bash
agy
```

Completa el inicio de sesión con tu cuenta Google.

Una vez dentro puedes seleccionar:

```text
/model
/effort high
```

---

# PASO 5 — Ya no necesitas configurar DealHunter manualmente

NO clones el repositorio.
NO busques coordenadas.
NO escribas cron.
NO instales dependencias manualmente.
NO necesitas saber Python.

Abre Codex o Antigravity y pega COMPLETO el siguiente prompt.

***

Quiero instalar y dejar completamente operativo DealHunter en este Android.

Repositorio oficial:

https://github.com/yorologo/DealHunter.git

Estoy ejecutando esta instrucción desde Termux mediante Codex o Antigravity.

OBJETIVO:

Partir del estado actual de este teléfono y terminar con la ÚLTIMA versión
de la rama main de DealHunter instalada, configurada, validada y funcionando,
incluyendo su actualización periódica automática de inventario.

KEEP IT SIMPLE, STUPID — KISS.

Trabaja autónomamente y no me hagas ejecutar manualmente cosas que puedas
hacer tú.

Sólo detente cuando Android, Shizuku, Rappi o una autenticación requieran
necesariamente mi intervención.

==================================================
1. OBTÉN DEALHUNTER
==================================================

Primero inspecciona el entorno.

Si DealHunter NO existe:

- elige una ubicación apropiada dentro de $HOME;
- clona:

  https://github.com/yorologo/DealHunter.git

- usa la rama main.

Si DealHunter YA existe:

- NO lo clones de nuevo;
- inspecciona git status;
- verifica el remote;
- fetch origin;
- actualiza main mediante fast-forward cuando sea seguro.

NO destruyas cambios locales existentes.

El objetivo es terminar utilizando el HEAD actual de origin/main.

==================================================
2. EL REPOSITORIO ES LA FUENTE DE VERDAD
==================================================

Antes de instalar/configurar nada lee:

- AGENTS.md
- README.md
- docs/
- pyproject.toml
- requirements*
- bin/
- src/
- tests/

El código ACTUAL de main manda sobre este prompt si algún comando,
path, puerto, schema o configuración ha cambiado.

NO inventes:

- comandos;
- flags;
- paths;
- puertos;
- coordenadas;
- radius;
- versiones;
- stores;
- endpoints.

==================================================
3. PREPARA TERMUX
==================================================

Comprueba:

- arquitectura;
- Android;
- Python;
- Git;
- dependencias necesarias;
- almacenamiento Android.

Instala únicamente las dependencias necesarias para DealHunter usando los
mecanismos normales de Termux y del proyecto.

No instales frameworks innecesarios.

==================================================
4. TEST GATE INICIAL
==================================================

Antes de configurar datos reales ejecuta la validación que corresponda al
checkout actual.

Como mínimo, si sigue siendo válido:

python -m pytest --collect-only -q
python -m pytest

Debe haber:

0 failed

Si un checkout limpio de main está roto:

DETENTE y explícame el problema.

No construyas mi instalación encima de código roto.

==================================================
5. SHIZUKU + RISH
==================================================

Comprueba si Shizuku está instalado, iniciado y Termux autorizado.

Localiza los archivos exportados por Shizuku.

Normalmente estarán bajo:

$HOME/storage/downloads/shizuku/

y deben incluir:

rish
rish_shizuku.dex

Pero VERIFICA las rutas reales.

Si faltan:

DETENTE y dime únicamente que debo:

1. abrir Shizuku;
2. iniciar Shizuku;
3. autorizar Termux;
4. entrar en "usar Shizuku en aplicaciones de terminal";
5. exportar los archivos;
6. volver aquí y responder "listo".

Cuando existan:

instala/configura rish usando el procedimiento CANÓNICO actual de DealHunter.

Comprueba especialmente:

RISH_APPLICATION_ID=com.termux

y ejecuta una prueba real equivalente a:

rish -c 'id'

Debe obtener identidad Android shell válida.

No modifiques ni destruyas los archivos originales exportados por Shizuku.

==================================================
6. RAPPI REAL
==================================================

Comprueba que la aplicación oficial de Rappi esté instalada.

Descubre su package actual en vez de asumirlo.

NO utilices el sitio Web de Rappi como sustituto silencioso de la app Android.

Durante setup:

NO compres.
NO modifiques carrito.
NO cambies métodos de pago.
NO realices ninguna acción comercial.

==================================================
7. SESIÓN RAPPI
==================================================

Inspecciona el mecanismo ACTUAL de Session Management de DealHunter.

Si ya existe una sesión usable:

valídala mediante las reglas actuales del proyecto.

Si NO existe:

inicia la Web/Wizard de DealHunter y guíame para obtener/configurar una
sesión legítima mediante el procedimiento actual.

No inventes tokens.
No marques una sesión VALID manualmente.
No imprimas secretos.
No guardes Bearer tokens en logs, Git ni texto de diagnóstico.

Si necesito interactuar con Rappi para proporcionar la sesión:

DETENTE únicamente en ese punto y dame las instrucciones mínimas.

Después continúa automáticamente.

==================================================
8. UBICACIÓN REAL
==================================================

DealHunter debe utilizar la zona de entrega REAL que esté activa actualmente
en la app oficial de Rappi.

NUNCA uses coordenadas de ejemplo.

NUNCA utilices:

- centro de una ciudad;
- coordenadas del README;
- coordenadas hardcodeadas;
- fallback geográfico.

Obtén/verifica la ubicación mediante los mecanismos reales disponibles en
DealHunter/Rappi/Shizuku.

Configúrala utilizando la configuración canónica actual.

Si no puedes demostrar razonablemente que corresponde a la zona activa de
Rappi:

DETENTE.

No ejecutes el crawler con una ubicación inventada.

==================================================
9. INSTALACIÓN Y CONFIGURACIÓN
==================================================

Instala DealHunter utilizando el procedimiento CANÓNICO del checkout actual.

Configura únicamente aquello que realmente requiera el proyecto.

Respeta:

CLI explícito
>
profile
>
configuración persistente

o la precedencia que el código actual defina.

No hardcodees configuración personal en source.

==================================================
10. INVENTARIO COMPLETO INICIAL
==================================================

Ejecuta UN Full Zone Inventory real.

Debe utilizar:

- sesión real;
- ubicación real;
- discovery actual;
- adapters actuales;
- ingestión completa.

IMPORTANTE:

DealHunter debe adquirir todos los productos válidos aunque no tengan
descuento.

Los filtros como min_discount pertenecen a la presentación/análisis,
no deben eliminar productos durante ingestion.

Deja que el baseline termine completamente.

No lo abortes porque tarde varios minutos.

==================================================
11. VALIDA EL BASELINE
==================================================

Comprueba desde DB y Web:

- run COMPLETED;
- merchants descubiertos;
- stores procesados;
- stores con productos;
- vacíos/no disponibles;
- failures;
- productos únicos;
- observations;
- Market;
- Turbo;
- Restaurantes.

No declares éxito únicamente porque pytest pase.

Debe existir inventario REAL.

==================================================
12. CONFIGURA EL SCHEDULER
==================================================

Utiliza EXCLUSIVAMENTE el mecanismo de scheduler que implemente el main
actual de DealHunter.

No escribas un cron paralelo si DealHunter ya incluye uno.

Configura un Full Zone Inventory automático diario según la regla actual en `main`
(actualmente esperamos 10:00 a. m. hora LOCAL, pero verifica esto).

Requisitos:

- máximo una ejecución simultánea;
- protección contra runs duplicados;
- registro de ejecución programada;
- logs/estado visibles;
- respetar 429/backoff;
- 401 según SessionStatus actual;
- no depender de tener el navegador abierto.

Comprueba:

- crontab/scheduler instalado;
- crond o mecanismo equivalente ejecutándose;
- próxima ejecución visible/correcta.

No dejes horarios temporales usados durante pruebas.

==================================================
13. ANDROID / REINICIOS
==================================================

Haz que la instalación sea tan persistente como permitan Termux y Android.

Comprueba batería/restricciones si es necesario.

No prometas persistencia que Android no garantice.

Si después de reiniciar Android el usuario debe volver a iniciar:

- Shizuku;
- crond;
- otro componente;

documenta exactamente qué debe hacer.

Si el proyecto ya dispone de un mecanismo seguro/canónico de arranque,
configúralo.

No inventes uno innecesariamente.

==================================================
14. WEB
==================================================

Descubre el comando, host y puerto ACTUALES desde el repo.

Inicia DealHunter Web.

Comprueba sus rutas principales reales.

Dame al terminar:

- comando para iniciar;
- URL Android localhost;
- URL LAN si el proyecto permite LAN.

No abras el servicio a Internet.

==================================================
15. ABRIR EN RAPPI
==================================================

Si sigue existiendo esta funcionalidad:

valida Web
→ DealHunter
→ rish/Shizuku
→ aplicación oficial de Rappi
→ tienda correcta.

No uses browser fallback silencioso.

==================================================
16. PRIVACIDAD
==================================================

Nunca incluyas en Git:

- tokens;
- session.enc;
- config personal;
- DB del usuario;
- logs personales;
- screenshots;
- cookies;
- rish exportado;
- DEX exportado;
- coordenadas personales.

Revisa git status.

==================================================
17. VALIDACIÓN FINAL
==================================================

Ejecuta la suite completa correspondiente a main.

Como mínimo, si sigue siendo el contrato actual:

python -m compileall src bin
PYTHONPATH=src pytest
git diff --check

Debe quedar:

0 failed

No cambies código del proyecto salvo encontrar un bug GENERAL real.

No hagas push de datos/configuración del usuario.

==================================================
18. TERMINA SÓLO CUANDO SEA UTILIZABLE
==================================================

No me devuelvas una lista de pasos que tú mismo puedas ejecutar.

Hazlos.

Sólo solicita mi ayuda para acciones humanas inevitables.

Al final devuelve:

DEALHUNTER FIRST-RUN SETUP COMPLETE

Repository:
- path
- branch
- HEAD

Environment:
- Termux
- Python

Shizuku/rish:
- Shizuku running
- Termux authorized
- rish PASS

Rappi:
- app PASS
- session status

Zone:
- configured
- verified

Baseline:
- run_id
- status
- merchants
- stores with products
- unique products
- observations

Scheduler:
- enabled
- schedule
- next run
- concurrency protection
- scheduler process

Web:
- command
- Android URL
- LAN URL if enabled

Tests:
- passed
- failed

Privacy:
- secrets tracked YES/NO

Blockers:
- NONE / detalle concreto

***

La IA se encargará de:

- descargar el último `main` de DealHunter;
- instalar dependencias;
- comprobar tests;
- instalar/configurar `rish`;
- comprobar Shizuku;
- comprobar Rappi;
- ayudarte a configurar una sesión real;
- detectar la zona real de Rappi;
- configurar DealHunter;
- crear el primer inventario completo;
- comprobar que los productos aparecen;
- iniciar la Web;
- programar el Full Zone Inventory automático;
- comprobar que el scheduler funciona.

Sólo te pedirá ayuda cuando Android o una cuenta requieran una acción humana.

---

# Después de instalar

Normalmente sólo necesitarás:

1. mantener Shizuku iniciado;
2. abrir DealHunter cuando quieras consultar ofertas;
3. renovar la sesión Rappi cuando realmente expire.

DealHunter mantendrá automáticamente su inventario mediante las
ejecuciones programadas.

Después de reiniciar Android comprueba que:

- Shizuku esté iniciado;
- Termux siga autorizado;
- el scheduler de DealHunter esté funcionando (e.g. `crond`).

La Web de DealHunter indicará su estado.

---

## Troubleshooting rápido (Resolución de problemas)

Si algo falla, consulta estas soluciones comunes:

- **Shizuku no está running o Termux no autorizado**: Vuelve a iniciar la app Shizuku, conecta la depuración inalámbrica y permite el acceso a Termux. [Más info](https://shizuku.rikka.app/guide/setup/).
- **Archivos `rish` no exportados**: Entra a Shizuku y usa la opción explícita "Exportar archivos" desde "Usar Shizuku en aplicaciones de terminal".
- **Problemas iniciando Codex/Antigravity**: Si el comando de inicio o el login fallan, consulta el [manual completo de Instalación en Termux](installation-termux.md).
- **El scheduler no corre tras reiniciar**: Android apaga `crond` y Termux al reiniciar. Debes volver a abrir Termux, iniciar Shizuku, y ejecutar el comando del daemon (por ejemplo `crond`). [Revisa la guía completa para persistencia](installation-termux.md).
- **Sesión de Rappi expirada**: La IA te pedirá revalidarla y actualizarla usando el mecanismo oficial de DealHunter, o puedes consultar los [Diagnósticos de Cuenta](account-diagnostics.md) para hacerlo tú mismo.
