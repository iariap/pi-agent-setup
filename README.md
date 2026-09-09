# Pi: implementación económica y razonamiento de frontera

Perfil personal reproducible de Pi Coding Agent y pi-subagents, capturado el **9 de septiembre de 2026**. GLM‑5.3 Flash realiza el trabajo habitual; GPT‑5.6 Sol se reserva para planificación, revisión compleja y decisiones difíciles. El objetivo es reducir el costo por cambio aceptado sin sacrificar validación.

## Instalación

### Instalación en una línea

El repositorio es privado: una URL anónima de `raw.githubusercontent.com` no permite
descargarlo. Autenticá GitHub CLI con `gh auth login --hostname github.com` y ejecutá:

```bash
gh api --hostname github.com repos/iariap/pi-agent-setup/contents/install.sh -H 'Accept: application/vnd.github.raw+json' | bash
```

Equivalente usando HTTPS y `curl`, aprovechando la autenticación guardada de GitHub CLI:

```bash
curl -fsSL -H "Authorization: Bearer $(gh auth token --hostname github.com)" -H 'Accept: application/vnd.github.raw+json' 'https://api.github.com/repos/iariap/pi-agent-setup/contents/install.sh?ref=main' | bash
```

Opciones del instalador se pasan con `bash -s --`. Por ejemplo, para revisar los destinos:

```bash
gh api --hostname github.com repos/iariap/pi-agent-setup/contents/install.sh -H 'Accept: application/vnd.github.raw+json' | bash -s -- --dry-run
```

También admite `--config-only`, `--no-shell-config` y `--root /otro/home`. El bootstrap necesita Bash,
GitHub CLI autenticado, Python 3, tar y mktemp; la instalación completa necesita Node/npm
según los requisitos de abajo. Descarga el repo a un temporal, ejecuta el instalador y
limpia ese temporal al terminar. No requiere un clon permanente ni cambia la raíz:
por defecto siempre usa el home del usuario actual.

Para una revisión reproducible, usá el mismo SHA en el parámetro `?ref=SHA` de la
descarga inicial y en `PI_SETUP_REF=SHA bash`. El bootstrap resuelve la referencia a un
commit antes de bajar el archivo completo. No publica el repo ni guarda tokens en archivos.

### Instalación desde un clon

Requisitos: Linux o macOS (WSL en Windows), Git, Python 3.9+, Node.js 22.19.0+ y npm. Para clonar el repo privado necesitás autenticar GitHub CLI o Git con tu propia cuenta.

```bash
gh repo clone iariap/pi-agent-setup
cd pi-agent-setup
python3 scripts/install.py --dry-run
python3 scripts/install.py
export PATH="$HOME/.local/bin:$PATH"
pi
```

El instalador configura PATH en `.profile`, `.bashrc` y `.zshrc`; la línea `export` del ejemplo activa el cambio también en la terminal actual. Usá `--no-shell-config` si administrás tus dotfiles con otra herramienta o usás otro shell. No uses `sudo`. **La raíz es el home del usuario que ejecuta el instalador**, resuelto con `Path.home()`; no depende del directorio del clon ni contiene un nombre de usuario fijo. Los destinos son:

- `~/.local/share/pi-dev`: instalación aislada de Pi.
- `~/.local/bin/pi`: acceso al ejecutable; si hay un launcher anterior se respalda antes de reemplazarlo.
- `~/.pi/agent/settings.json`: configuración global de tu usuario.
- `~/.pi/agent/agents/*.md`: agentes personalizados.
- `~/.pi/agent/backups/pi-agent-setup-<fecha>`: respaldo de cada archivo modificado y manifiesto de archivos previamente inexistentes.
- `~/.pi/agent/backups/pi-runtime-<fecha>`: respaldo del launcher y archivos de shell modificados, con rutas relativas al home en el manifiesto.

### Si Pi ya está instalado

**Ejecutá el mismo comando de instalación.** Instala o actualiza la copia administrada a las versiones de `config/versions.json`, instala las extensiones fijadas y vuelve a aplicar los agentes y modelos del perfil. Si había otra versión más nueva, también converge a estas versiones probadas: no sigue `latest` automáticamente.

La instalación administrada queda primera en PATH para nuevas terminales Bash/Zsh. Las instalaciones anteriores en otros directorios no se desinstalan. Las credenciales, sesiones y ajustes ajenos al perfil se conservan. Los bloques de PATH y paquetes administrados no se duplican al repetir el comando; los cambios locales en campos/agentes administrados se respaldan y reemplazan por el perfil.

Abrí una terminal nueva o ejecutá `~/.local/bin/pi` para usarla inmediatamente. Un script ejecutado por pipe no puede cambiar el entorno de la terminal padre. Si tenés un alias o una función llamada `pi`, o un gestor que modifica PATH después de estos archivos, verificá con `type -a pi`; el ejecutable absoluto siempre selecciona esta instalación.

Si ya tenés Pi y las extensiones compatibles instaladas, podés aplicar sólo el perfil:

```bash
python3 scripts/install.py --config-only
```

`--config-only` no descarga extensiones: en otra máquina instalá las versiones indicadas abajo si faltan. `--root /otro/home` permite probar en un destino aislado. La configuración de un proyecto en `.pi/settings.json` puede prevalecer sobre este perfil global.

### Autenticación y versiones

Dentro de Pi ejecutá `/login` y autenticá **OpenRouter** y **OpenAI Codex**. Necesitás acceso efectivo a los modelos en ambas cuentas. El instalador no copia credenciales ni inicia sesiones. Usá `pi update --models` y `/model` para revisar el catálogo disponible. Reiniciá Pi después de aplicar el perfil.

Versiones fijadas en `config/versions.json`:

- `@earendil-works/pi-coding-agent@0.85.1`.
- `pi-subagents@0.66.0` (la versión instalada en el directorio de paquetes de Pi, no una instalación global antigua).
- `pi-ask-user@0.15.0`.

El instalador usa npm sin scripts de instalación para Pi y `pi install` para las extensiones. Si falla una descarga, termina con error y podés volver a ejecutarlo. Las versiones directas están fijadas; las dependencias transitivas y el comportamiento de los proveedores no quedan congelados por este repositorio.

## Asignación efectiva de modelos

La sesión principal utiliza `openrouter/z-ai/glm-5.3-flash`, razonamiento `medium`. El mismo modelo es el default de subagentes sin modelo propio. Los siguientes roles tienen overrides explícitos:

- `scout`, `tester`: **GLM low**, búsqueda de archivos y ejecución de comprobaciones.
- `delegate`, `synthesizer`: **GLM medium**, tareas acotadas, planes sencillos, revisión rutinaria y consolidación de evidencia.
- `coder`, `worker`, `pathfinder`: **GLM high**, implementación y diagnóstico donde reducir demasiado el razonamiento puede generar retrabajo.
- `planner`, `reviewer`: **Sol high**, trabajos complejos, ambiguos o de impacto elevado.
- `oracle`: **Sol xhigh**, escalación excepcional ante contradicciones, decisiones relevantes o diagnósticos fallidos.

Se conserva el proveedor `openai-codex` para Sol. No se sustituye silenciosamente por una API paga. Todos estos roles usan `defaultContext: fresh` y `fast: false`. El modelo de GLM está fijado a una versión concreta para evitar que un alias `latest` cambie el perfil sin revisión.

Los agentes `worker`, `delegate` y `oracle` provienen de pi-subagents. Los otros prompts personalizados están versionados en `agents/`; sus campos coinciden con los overrides. También se conservan dos archivos preexistentes para reproducir la carpeta: `code-analyzer` está especializado en V y no debe asignarse a un repositorio Python/TypeScript sin adaptación; `supervisor` es una plantilla de Taskplane y requiere ese sistema para su uso previsto. Este instalador no instala Taskplane.

La configuración sólo orienta la selección mediante nombres y descripciones. **No es un clasificador de complejidad ni un límite duro de gasto.** Una invocación explícita de `planner` o `reviewer` usa Sol aunque la tarea sea simple. Overrides por ejecución y por proyecto también pueden cambiar el resultado.

## Por qué funciona esta distribución

Implementar un contrato claro suele requerir menos razonamiento abierto que decidir qué construir, resolver una migración o detectar una falla de autorización. El modelo económico recibe pasos verificables; el modelo de frontera recibe la incertidumbre que justifica su costo. Un modelo más caro no garantiza mejores resultados y dos agentes pueden compartir el mismo error: el cierre depende de pruebas y evidencia.

Flujos recomendados:

1. Cambio pequeño: `coder → tester`. El agente principal puede resolverlo sin delegar si el costo de coordinación no se justifica.
2. Feature compleja: `scout → planner → coder → tester → reviewer`.
3. Bug: `scout → pathfinder → coder → tester`. Después de dos intentos fallidos sin evidencia nueva, consultar `oracle`; no repetir indefinidamente.
4. Autenticación, RLS, permisos, migraciones o reglas críticas: plan explícito, pruebas de invariantes y revisión Sol; usar `xhigh` por ejecución cuando la dificultad lo amerite.

En un sistema de alimentación, por ejemplo, una tarjeta de receta acotada puede implementarse con GLM. Los límites entre usuarios, alergias, sustituciones y consistencia de un plan merecen revisión más profunda y validación determinista. El LLM no sustituye las reglas del dominio.

## Tokens y contexto

`fresh` evita copiar automáticamente toda la conversación del padre. No elimina instrucciones, archivos recuperados ni salidas de herramientas; una invocación explícita puede pedir contexto heredado. Tampoco garantiza ahorro: un handoff pobre puede obligar al agente a investigar todo de nuevo.

Cada delegación debe contener objetivo, archivos relevantes, decisiones ya tomadas, restricciones, pruebas y criterio de cierre. Pasar rutas y fragmentos pertinentes en vez de archivos completos; compartir artefactos breves entre etapas. Oracle necesita recibir explícitamente las decisiones previas con este perfil fresco, porque su prompt base está orientado a preservar contexto heredado.

`high` y `xhigh` son controles de esfuerzo, no una cantidad fija de tokens. Su interpretación depende del proveedor y de la versión de Pi. `fast: false` evita solicitar el modo prioritario soportado por la extensión; no limita todos los cargos posibles. No se agregan límites de salida arbitrarios que puedan truncar un parche o una validación.

Optimizar tokens y dinero no siempre coincide: un modelo barato puede emitir más tokens y tardar más. Hay que medir también tiempo de herramientas, cola del proveedor, iteraciones y atención humana. Mantener prefijos estables puede favorecer cache; cambiar de proveedor o modelo puede perderlo.

## Costos: API, suscripción y ejemplos

**Este perfil paga GLM por OpenRouter y consume el acceso/cuota de OpenAI Codex para Sol.** Los tokens Sol no se pueden convertir automáticamente en dólares por API ni en porcentaje de cuota. Si la suscripción ya existe, puede no haber cargo marginal por cada llamada, pero sí límites y costo de oportunidad. Los valores internos del catálogo de Pi son estimaciones, no una factura.

Para comparar arquitecturas se usan tarifas de referencia sin promociones: GLM **USD 0,15 entrada / 0,50 salida por millón** y Sol API **USD 4 / 20**. Son una referencia consultada el 9/9/2026, no una promesa de facturación; verificar proveedor, cache, impuestos y cargos vigentes. La promoción GLM de 0,075/0,25 anunciaba vencimiento el 9/9 a las 16:00 UTC. [OpenRouter GLM](https://openrouter.ai/z-ai/glm-5.3-flash), [comparación de precios de Artificial Analysis](https://artificialanalysis.ai/models/comparisons/glm-5-3-flash-vs-gpt-5-6-sol).

Ejemplo hipotético sin cache, con **entrada acumulada entre todas las llamadas**, no tamaño de un solo prompt:

- Plan: 20.000 tokens de entrada y 3.000 de salida.
- Implementación: 180.000 de entrada y 20.000 de salida.
- Revisión: 40.000 de entrada y 3.000 de salida.
- La salida incluye razonamiento facturable; no volver a sumarlo si ya está incluido en la telemetría.

Con un intento: todo GLM equivale a **USD 0,049**, Sol→GLM→Sol a **USD 0,397** y todo Sol API a **USD 1,48**. El híbrido reduce un 73,2% el gasto de referencia respecto a todo Sol, bajo exactamente esos supuestos. No demuestra igual calidad ni igual cantidad de tokens entre modelos.

En el perfil realmente configurado, ese híbrido representa **USD 0,037 de GLM** más **60.000 tokens de entrada y 6.000 de salida de Sol contra su acceso/cuota**. Cien tareas iguales serían USD 3,70 de GLM más ese uso de Sol multiplicado por cien, y la suscripción/créditos que correspondan; no USD 39,70 de factura API. El orquestador, herramientas y revisión humana están excluidos del ejemplo.

Con un segundo intento completo y otra revisión, el híbrido API de referencia sube a **USD 0,654**. Las fallas agregan tanto implementación como revisión: a veces ahorrar en el ejecutor cuesta más por retrabajo. El modelo general es:

```text
costo llamada = (entrada sin cache × tarifa entrada
               + entrada cacheada × tarifa cache
               + salida facturable × tarifa salida) / 1.000.000
costo por tarea aceptada = gasto de todas las ejecuciones / tareas aceptadas
costo total operativo = gasto modelos + herramientas + tiempo humano valorado
```

Calculadora reproducible, sin dependencias ni llamadas a modelos:

```bash
python3 scripts/costs.py
python3 scripts/costs.py --attempts 2 --output-multiplier 1.5
```

El multiplicador prueba sensibilidad a la verbosidad, no estima automáticamente lo que hará cada modelo. Modificar las tarifas del script cuando cambien; todos sus resultados son simulaciones.

## Prestaciones y calidad de la evidencia

Artificial Analysis v4.3 reporta GLM Flash 42 y Sol max 47 en su índice; Terminal-Bench v4 33%/40% y SciCode 52%/57%. El costo ponderado por tarea es 0,25/1,99 USD; GLM produce más salida (69k frente a 29k por tarea). Esto respalda probar GLM como ejecutor económico, pero el índice no mide este harness ni planificación por rol. **Sol max no es el Sol high configurado en planner/reviewer.** No se extrapola su resultado a esos agentes. [Evaluación independiente](https://artificialanalysis.ai/models/comparisons/glm-5-3-flash-vs-gpt-5-6-sol).

Experiencias públicas señalan degradación de GLM en conversaciones largas y verificaciones afirmadas sin evidencia. El debate high/max es contradictorio. Usuarios de Sol reportan sobreingeniería en tareas abiertas. Son testimonios con sesgo de selección, distintos modelos/proveedores y sin control experimental; sirven para definir fallos a observar, no para prometer ahorros. [GLM: sesiones largas](https://www.reddit.com/r/LocalLLaMA/comments/1w2germ/glm53flash_is_100_a_step_change_in_agential/), [GLM: high/max](https://www.reddit.com/r/ZaiGLM/comments/1w0cfrj/psa_you_must_use_glm53flash_in_max_reasoning_mode/), [Sol: sobreingeniería](https://www.reddit.com/r/codex/comments/1uuo6x4/how_to_keep_gpt56_sol_high_from_overengineering/).

Para validar el perfil: usar 20–30 tareas representativas, misma revisión inicial del repositorio, criterios y pruebas. Comparar GLM solo, híbrido y Sol solo con presupuestos de intentos equivalentes; alternar orden y repetir casos. Registrar tokens reales por clase, hits de cache, gasto, tiempo hasta aceptación, correcciones humanas, falsas afirmaciones de éxito y regresiones. Revisar el diff sin conocer el modelo cuando sea posible. Las pruebas verdes no bastan si no cubren los requisitos. No hay una tasa de éxito local medida en este repositorio.

## Respaldo, seguridad y mantenimiento

`config/settings.json` es una exportación permitida de campos del perfil, no una copia completa de la cuenta. No contiene claves, sesiones, memoria, registros ni el cache del catálogo. La instalación preserva ajustes y extensiones ajenos al perfil. Reemplaza sólo campos de roles administrados, incluso sus overrides por proveedor que de otro modo anularían los modelos elegidos; el respaldo permite recuperar la configuración previa.

Para restaurar, cerrá Pi, consultá `manifest.json` en el respaldo y copiá los archivos con `existed: true` sobre sus rutas relativas dentro de `~/.pi/agent`. Los marcados `existed: false` fueron creados por la instalación: retiralos sólo si no tienen cambios posteriores que quieras conservar. Esto revierte archivos de configuración, no desinstala binarios o dependencias descargadas.

Los respaldos `pi-runtime-*` usan un manifiesto distinto, con `relative_to: user home`: sus rutas se restauran respecto del home, preservando enlaces simbólicos. Si un archivo de inicio del shell es un symlink, el instalador se detiene antes de cambiarlo y permite optar por `--no-shell-config`.

Los prompts de sólo lectura son instrucciones de comportamiento: una herramienta `bash` puede escribir si no hay controles adicionales. Esta distribución no instala un sandbox ni debe describirse como tal. No se añaden fallbacks automáticos a modelos caros. Actualizá versiones y modelos en una rama y repetí la evaluación antes de adoptar otro `latest`.

Pruebas locales del instalador, sin consumir tokens:

```bash
python3 -m unittest discover -s tests -v
```

Fuentes de funcionamiento: [Pi](https://pi.dev/), [selección de modelos en pi-subagents](https://github.com/nicobailon/pi-subagents/blob/main/docs/models.md), [definición de agentes](https://github.com/nicobailon/pi-subagents/blob/main/docs/agents.md). La lógica de instalación usa las versiones fijadas; documentación upstream puede cambiar.
