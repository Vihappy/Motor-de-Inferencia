"""
Sistemas Expertos - Identificador de conectores lógicos
Texto -> Tokens -> Conectores -> Átomos -> Reglas -> Árbol semántico -> Modelos
Cada oración digitada se guarda en una tabla y en la base de conocimiento.
"""
import sys
import string
import textwrap
import unicodedata

# Evita problemas con los símbolos (∧ ∨ Δ ⇒ ↔) en terminales de Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Tabla de la imagen "Conectores_Logicos":
# clave: (símbolo, operación lógica, esquema, significado)
CONECTORES = {
    "conjuncion":           ("∧", "Conjunción",           "p ∧ q", "p y q"),
    "disyuncion":           ("∨", "Disyunción",           "p ∨ q", "p o q"),
    "disyuncion_exclusiva": ("Δ", "Disyunción exclusiva", "p Δ q", "o p o q"),
    "condicional":          ("⇒", "Condicional",          "p ⇒ q", "si p entonces q"),
    "bicondicional":        ("↔", "Bicondicional",        "p ↔ q", "p si y solo si q"),
    "negacion":             ("~", "Negación",             "~ p",   "no p"),
}

# Símbolo de cada tipo de nodo de la fórmula
SIMBOLOS = {"y": "∧", "o": "∨", "xor": "Δ", "cond": "⇒", "bicond": "↔"}

BICOND = ["si", "y", "solo", "si"]  # "si y solo si" son 4 palabras
LETRAS = "pqrstuvwxyz"
ANCHO_LINEA = 64


# ─────────────────────────── TEXTO Y CONECTORES ───────────────────────────

def sin_acentos(texto):
    """Quita acentos solo para comparar (sí -> si, ó -> o)."""
    return "".join(c for c in unicodedata.normalize("NFD", texto)
                   if unicodedata.category(c) != "Mn")


def tokenizar(oracion):
    """Convierte a minúsculas y separa por espacios (quitando signos de puntuación)."""
    tokens = []
    for palabra in oracion.lower().split():
        palabra = palabra.strip(string.punctuation + "¡¿")
        if palabra:
            tokens.append(palabra)
    return tokens


def detectar_conectores(tokens):
    """Devuelve (conectores, avisos). Cada conector es (posición, texto, clave)."""
    k = [sin_acentos(t) for t in tokens]
    encontrados = []
    avisos = []

    exclusiva = bool(k) and k[0] == "o" and k.count("o") >= 2
    o_vistas = 0
    i = 0
    while i < len(k):
        if k[i:i + 4] == BICOND:
            encontrados.append((i, "si y solo si", "bicondicional"))
            i += 4
            continue
        if k[i] == "si":
            if "entonces" in k[i + 1:]:
                encontrados.append((i, "si ... entonces", "condicional"))
            else:
                avisos.append("Hay un 'si' sin su 'entonces'.")
        elif k[i] == "entonces":
            if "si" not in k[:i]:
                avisos.append("Hay un 'entonces' sin su 'si'.")
        elif k[i] == "o":
            if exclusiva and o_vistas < 2:
                if o_vistas == 0:
                    encontrados.append((i, "o ... o", "disyuncion_exclusiva"))
            else:
                encontrados.append((i, "o", "disyuncion"))
            o_vistas += 1
        elif k[i] == "y":
            encontrados.append((i, "y", "conjuncion"))
        elif k[i] == "no":
            encontrados.append((i, "no", "negacion"))
        i += 1
    return encontrados, avisos


# ─────────────────────────── FÓRMULAS ───────────────────────────
# Una fórmula es una tupla:
#   ("atomo", "p")         ("no", f)
#   ("y" | "o" | "xor" | "cond" | "bicond", izquierda, derecha)

def parsear(tokens, atomos):
    """Traduce los tokens a una fórmula (de menor a mayor precedencia:
    ↔, ⇒, Δ, ∨, ∧, ~). 'atomos' es un diccionario frase -> letra que se
    comparte entre todas las oraciones (misma frase = misma letra)."""
    if not tokens:
        raise ValueError("Falta una proposición a un lado de un conector.")
    k = [sin_acentos(t) for t in tokens]

    # Bicondicional: p si y solo si q
    for i in range(len(k) - 3):
        if k[i:i + 4] == BICOND:
            izq = parsear(tokens[:i], atomos)
            der = parsear(tokens[i + 4:], atomos)
            return ("bicond", izq, der)

    # Condicional: si p entonces q
    if k[0] == "si" and "entonces" in k:
        j = k.index("entonces")
        izq = parsear(tokens[1:j], atomos)
        der = parsear(tokens[j + 1:], atomos)
        return ("cond", izq, der)

    # Disyunción exclusiva: o p o q
    if k[0] == "o" and "o" in k[1:]:
        j = k.index("o", 1)
        izq = parsear(tokens[1:j], atomos)
        der = parsear(tokens[j + 1:], atomos)
        return ("xor", izq, der)

    # Disyunción: p o q
    if "o" in k:
        j = k.index("o")
        izq = parsear(tokens[:j], atomos)
        der = parsear(tokens[j + 1:], atomos)
        return ("o", izq, der)

    # Conjunción: p y q
    if "y" in k:
        j = k.index("y")
        izq = parsear(tokens[:j], atomos)
        der = parsear(tokens[j + 1:], atomos)
        return ("y", izq, der)

    # Negación: no p
    if k[0] == "no":
        return ("no", parsear(tokens[1:], atomos))

    # Átomo: proposición simple
    frase = " ".join(tokens)
    if frase not in atomos:
        n = len(atomos)
        atomos[frase] = LETRAS[n] if n < len(LETRAS) else f"p{n}"
    return ("atomo", atomos[frase])


def formato(f, raiz=True):
    """Convierte una fórmula a texto, por ejemplo (p ∧ q) ↔ ~r."""
    if f[0] == "atomo":
        return f[1]
    if f[0] == "no":
        return "~" + formato(f[1], False)
    texto = f"{formato(f[1], False)} {SIMBOLOS[f[0]]} {formato(f[2], False)}"
    return texto if raiz else f"({texto})"


def neg(f):
    """Negación de una fórmula (evita dobles negaciones)."""
    return f[1] if f[0] == "no" else ("no", f)


def atomos_en(f, lista=None):
    """Letras de los átomos que aparecen en la fórmula, en orden."""
    if lista is None:
        lista = []
    if f[0] == "atomo":
        if f[1] not in lista:
            lista.append(f[1])
    else:
        for sub in f[1:]:
            atomos_en(sub, lista)
    return lista


def es_literal(f):
    return f[0] == "atomo" or (f[0] == "no" and f[1][0] == "atomo")


def literal(f):
    """Un literal como (letra, valor): p -> ('p', True), ~p -> ('p', False)."""
    return (f[1], True) if f[0] == "atomo" else (f[1][1], False)


# ─────────────────────────── ÁRBOL SEMÁNTICO (TABLEAU) ───────────────────────────

class Nodo:
    """Un nodo del árbol semántico."""

    def __init__(self, etiqueta="", origen=""):
        self.etiqueta = etiqueta   # fórmulas con las que nace la rama
        self.origen = origen       # regla (R1, R2...) que se descompuso
        self.notas = []            # descomposiciones sin ramificar (∧, ~∨, ...)
        self.hijos = []
        self.estado = None         # "cerrada" | "abierta" | None
        self.detalle = ""          # motivo de cierre
        self.modelo = None         # átomos -> True/False de una rama abierta


def descomponer(f):
    """Clasifica una fórmula según el método del tableau:
    ('literal', None)          -> átomo o átomo negado
    ('alfa', [partes])         -> todas las partes siguen en la misma rama
    ('beta', [rama1, rama2])   -> la rama se divide en dos"""
    if f[0] == "atomo":
        return "literal", None
    if f[0] == "no":
        g = f[1]
        if g[0] == "atomo":
            return "literal", None
        if g[0] == "no":
            return "alfa", [g[1]]
        a, b = g[1], g[2]
        if g[0] == "y":                       # ~(A ∧ B)  =>  ~A | ~B
            return "beta", [[neg(a)], [neg(b)]]
        if g[0] == "o":                       # ~(A ∨ B)  =>  ~A, ~B
            return "alfa", [neg(a), neg(b)]
        if g[0] == "cond":                    # ~(A ⇒ B)  =>  A, ~B
            return "alfa", [a, neg(b)]
        if g[0] == "bicond":                  # ~(A ↔ B)  =>  (A, ~B) | (~A, B)
            return "beta", [[a, neg(b)], [neg(a), b]]
        return "beta", [[a, b], [neg(a), neg(b)]]   # ~(A Δ B)
    a, b = f[1], f[2]
    if f[0] == "y":                           # A ∧ B  =>  A, B
        return "alfa", [a, b]
    if f[0] == "o":                           # A ∨ B  =>  A | B
        return "beta", [[a], [b]]
    if f[0] == "cond":                        # A ⇒ B  =>  ~A | B
        return "beta", [[neg(a)], [b]]
    if f[0] == "bicond":                      # A ↔ B  =>  (A, B) | (~A, ~B)
        return "beta", [[a, b], [neg(a), neg(b)]]
    return "beta", [[a, neg(b)], [neg(a), b]]       # A Δ B


ORDEN_CLASE = {"literal": 0, "alfa": 1, "beta": 2}


def expandir(nodo, pendientes, literales, modelos):
    """Construye el árbol. 'pendientes' son (fórmula, regla) por descomponer y
    'literales' los átomos ya fijados en la rama (átomo -> True/False)."""
    literales = dict(literales)
    pendientes = list(pendientes)
    while pendientes:
        # Primero los literales, luego las reglas sin ramas y al final las que ramifican
        pendientes.sort(key=lambda it: ORDEN_CLASE[descomponer(it[0])[0]])
        f, origen = pendientes.pop(0)
        clase, partes = descomponer(f)

        if clase == "literal":
            letra, valor = literal(f)
            if letra in literales and literales[letra] != valor:
                nodo.estado = "cerrada"                 # X y ~X  =>  rama cerrada ✗
                nodo.detalle = f"{letra} y ~{letra}"
                return
            literales[letra] = valor

        elif clase == "alfa":
            nodo.notas.append(f"{origen}: {formato(f)}  ⇒  "
                              + ", ".join(formato(p) for p in partes))
            pendientes += [(p, origen) for p in partes]

        else:  # beta: se crean dos ramas
            for rama in partes:
                hijo = Nodo(", ".join(formato(p) for p in rama), origen)
                nodo.hijos.append(hijo)
                expandir(hijo, pendientes + [(p, origen) for p in rama],
                         literales, modelos)
            return

    nodo.estado = "abierta"                             # rama abierta ✓
    nodo.modelo = literales
    modelos.append(literales)


def modelos_de(formulas):
    """Ramas abiertas del árbol de un conjunto de fórmulas (sus modelos)."""
    modelos = []
    expandir(Nodo(), [(f, "") for f in formulas], {}, modelos)
    return modelos


def condicion(modelo):
    """Texto tipo 'p=V, q=F' para un modelo."""
    if not modelo:
        return "cualquier valor"
    return ", ".join(f"{a}={'V' if v else 'F'}" for a, v in sorted(modelo.items()))


def dibujar_arbol(nodo, prefijo="  "):
    """Imprime el árbol con ramas ├─ └─ marcando las cerradas ✗ y abiertas ✓."""
    for i, hijo in enumerate(nodo.hijos):
        ultimo = i == len(nodo.hijos) - 1
        rama, cont = ("└─", "   ") if ultimo else ("├─", "│  ")
        if hijo.estado == "cerrada":
            marca = f"   ✗ CERRADA ({hijo.detalle})"
        elif hijo.estado == "abierta":
            marca = "   ✓ ABIERTA"
        else:
            marca = ""
        print(f"{prefijo}{rama}[{hijo.origen}] {hijo.etiqueta}{marca}")
        for nota in hijo.notas:
            print(f"{prefijo}{cont}   · {nota}")
        dibujar_arbol(hijo, prefijo + cont)


# ─────────────────────────── PANTALLA ───────────────────────────

def titulo(texto):
    """Línea de título tipo:  ── Texto ─────────"""
    relleno = max(ANCHO_LINEA - len(texto) - 4, 2)
    return f"── {texto} " + "─" * relleno


def mostrar_bienvenida():
    marco = "═" * (ANCHO_LINEA - 2)
    print("╔" + marco + "╗")
    print("║" + "SISTEMAS EXPERTOS  ·  Conectores lógicos".center(ANCHO_LINEA - 2) + "║")
    print("╚" + marco + "╝")
    mostrar_ayuda()


def mostrar_ayuda():
    print()
    print(titulo("Instrucciones"))
    print("  1. Escribe una oración en lenguaje común y presiona Enter.")
    print("  2. El programa la pasa a minúsculas y la separa por espacios.")
    print("  3. Detecta conectores y átomos, y la agrega a la tabla.")
    print("  4. Escribe 'arbol' para construir el árbol semántico con")
    print("     todas las oraciones y ver qué es verdadero o falso.")
    print()
    print(titulo("Conectores reconocidos"))
    for simbolo, operacion, _, significado in CONECTORES.values():
        print(f"  {simbolo:<2} {operacion:<22} {significado}")
    print()
    print(titulo("Comandos"))
    print("  arbol      → árbol semántico y valores de verdad")
    print("  historial  → ver la tabla acumulada")
    print("  reiniciar  → borrar todas las oraciones")
    print("  ayuda      → ver estas instrucciones")
    print("  salir      → terminar el programa")
    print("─" * ANCHO_LINEA)


def tabla_simple(encabezados, filas):
    """Tabla sencilla con bordes para listas de filas."""
    anchos = [max(len(str(x)) for x in col) for col in zip(encabezados, *filas)]

    def borde(izq, med, der):
        return izq + med.join("─" * (a + 2) for a in anchos) + der

    def fila(valores):
        return "│" + "│".join(f" {str(v):<{a}} " for v, a in zip(valores, anchos)) + "│"

    print(borde("┌", "┬", "┐"))
    print(fila(encabezados))
    print(borde("├", "┼", "┤"))
    for f in filas:
        print(fila(f))
    print(borde("└", "┴", "┘"))


def imprimir_tabla(registros):
    """Dibuja la tabla acumulada. Cada registro es un dict con:
    'oracion', 'atomos' (lista de (letra, frase)) y
    'filas' (lista de (operación, esquema, significado))."""
    encabezados = ["#", "Oración digitada", "Átomos",
                   "Operación lógica", "Esquema", "Significado"]
    max_oracion = 26
    max_atomo = 22

    # Cada registro es un bloque: una lista de líneas por columna
    grupos = []
    for reg in registros:
        oracion = textwrap.wrap(reg["oracion"], max_oracion) or [""]

        atomos = []  # cada átomo va en su propia línea
        for letra, frase in reg["atomos"]:
            atomos += textwrap.wrap(f"{letra} = {frase}", max_atomo,
                                    subsequent_indent="    ")
        atomos = atomos or ["—"]

        operaciones = [f[0] for f in reg["filas"]]
        esquemas = [f[1] for f in reg["filas"]]
        significados = [f[2] for f in reg["filas"]]
        grupos.append([[str(reg["n"])], oracion, atomos,
                       operaciones, esquemas, significados])

    # Anchos de columna
    anchos = [len(h) for h in encabezados]
    for grupo in grupos:
        for c, lineas in enumerate(grupo):
            anchos[c] = max(anchos[c], max(len(l) for l in lineas))

    def borde(izq, med, der):
        return izq + med.join("─" * (a + 2) for a in anchos) + der

    def fila(valores):
        return "│" + "│".join(f" {v:<{a}} " for v, a in zip(valores, anchos)) + "│"

    print(borde("┌", "┬", "┐"))
    print(fila(encabezados))
    for grupo in grupos:
        print(borde("├", "┼", "┤"))
        alto = max(len(lineas) for lineas in grupo)
        for r in range(alto):
            print(fila([lineas[r] if r < len(lineas) else "" for lineas in grupo]))
    print(borde("└", "┴", "┘"))


def analizar(oracion, atomos, n):
    """Analiza una oración (la número n), la muestra y devuelve su registro."""
    tokens = tokenizar(oracion)
    conectores, avisos = detectar_conectores(tokens)

    print()
    print(titulo("Análisis"))
    print("  Minúsculas :", oracion.lower())
    print("  Tokens     :", " | ".join(tokens))
    print("  Conectores :", ", ".join(f"«{t}»" for _, t, _ in conectores) or "ninguno")

    # Los átomos son compartidos entre oraciones; si hay error no se guardan
    copia = dict(atomos)
    ast = None
    lista_atomos = []
    try:
        ast = parsear(tokens, copia)
        atomos.clear()
        atomos.update(copia)
        inverso = {letra: frase for frase, letra in atomos.items()}
        for letra in atomos_en(ast):
            lista_atomos.append((letra, inverso[letra]))
            print(f"  Átomo {letra:<3}  : {inverso[letra]}")
        print("  Fórmula    :", formato(ast))

        # ¿La sentencia es verdadera o falsa? Se buscan las ramas abiertas de
        # su árbol y del árbol de su negación.
        verdaderas = modelos_de([ast])
        falsas = modelos_de([neg(ast)])
        if verdaderas and falsas:
            clase = "CONTINGENTE (puede ser verdadera o falsa)"
        elif verdaderas:
            clase = "TAUTOLOGÍA (siempre verdadera)"
        else:
            clase = "CONTRADICCIÓN (siempre falsa)"
        print("  Valor lógico:", clase)
        print("  Verdadera si:", " | ".join(condicion(m) for m in verdaderas) or "nunca")
        print("  Falsa si    :", " | ".join(condicion(m) for m in falsas) or "nunca")
    except ValueError as error:
        print("  ⚠ No se pudo construir la fórmula:", error)

    for aviso in avisos:
        print("  ⚠", aviso)

    # Filas para la tabla (una por conector encontrado)
    filas = []
    for _, _, clave in conectores:
        _, operacion, esquema, significado = CONECTORES[clave]
        filas.append((operacion, esquema, significado))
    if not filas:
        filas.append(("Proposición simple", "p", "sin conector"))

    return {"n": n, "oracion": oracion.strip(), "ast": ast,
            "atomos": lista_atomos, "filas": filas}


def mostrar_historial(registros):
    print()
    n = len(registros)
    print(titulo(f"Tabla acumulada ({n} {'oración' if n == 1 else 'oraciones'})"))
    if registros:
        imprimir_tabla(registros)
    else:
        print("  Aún no has digitado ninguna oración.")


def mostrar_arbol(registros, atomos):
    """Base de conocimiento -> árbol semántico -> resultado (modelos V/F)."""
    base = [r for r in registros if r["ast"] is not None]
    if not base:
        print("\n  ⚠ Primero escribe al menos una oración válida.")
        return
    inverso = {letra: frase for frase, letra in atomos.items()}

    # 04 - Base de conocimiento
    print()
    print(titulo("04 Base de conocimiento"))
    ancho = max(len(formato(r["ast"])) for r in base)
    for r in base:
        tipo = "HECHO" if es_literal(r["ast"]) else "REGLA"
        print(f"  R{r['n']:<2} {tipo:<6} {formato(r['ast']):<{ancho}}   «{r['oracion']}»")
    print("\n  Átomos:")
    for frase, letra in atomos.items():
        print(f"    {letra} = {frase}")

    # 05 - Árbol semántico
    print()
    print(titulo("05 Árbol semántico"))
    print("  1. Suponer todas las reglas verdaderas.")
    print("  2. Descomponer: A ⇒ B  se divide en  ~A | B.")
    print("  3. Si una rama tiene X y ~X, se cierra ✗.")
    print("  4. Las ramas abiertas ✓ son las condiciones válidas.")
    print()
    raiz = Nodo("  |  ".join(f"R{r['n']}: {formato(r['ast'])}" for r in base))
    modelos = []
    expandir(raiz, [(r["ast"], f"R{r['n']}") for r in base], {}, modelos)
    print(f"  Raíz: {raiz.etiqueta}")
    for nota in raiz.notas:
        print(f"    · {nota}")
    if raiz.estado == "cerrada":
        print(f"    ✗ CERRADA ({raiz.detalle})")
    dibujar_arbol(raiz)

    # 06 - Resultado
    print()
    print(titulo("06 Resultado"))
    if not modelos:
        print("  ✗ BASE DE CONOCIMIENTO INCONSISTENTE")
        print("    Todas las ramas se cerraron: las oraciones no pueden ser")
        print("    verdaderas al mismo tiempo.")
        return
    print(f"  ✓ MODELO ENCONTRADO · SATISFACIBLE  ({len(modelos)} "
          f"{'modelo' if len(modelos) == 1 else 'modelos'})")
    for i, modelo in enumerate(modelos, start=1):
        print(f"\n  Modelo {i} (rama abierta): todas las reglas se cumplen con")
        filas = []
        for frase, letra in atomos.items():
            if letra in modelo:
                valor = "VERDADERO" if modelo[letra] else "FALSO"
            else:
                valor = "indiferente (V o F)"
            filas.append((letra, frase, valor))
        tabla_simple(["Átomo", "Significado", "Valor"], filas)


def main():
    mostrar_bienvenida()
    registros = []   # oraciones digitadas (tabla y base de conocimiento)
    atomos = {}      # frase -> letra, compartido por todas las oraciones

    while True:
        try:
            entrada = input(f"\nOración #{len(registros) + 1} ➜ ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        comando = sin_acentos(entrada.lower())
        if comando == "salir":
            break
        if comando == "ayuda":
            mostrar_ayuda()
            continue
        if comando == "historial":
            mostrar_historial(registros)
            continue
        if comando == "arbol":
            mostrar_arbol(registros, atomos)
            continue
        if comando == "reiniciar":
            registros.clear()
            atomos.clear()
            print("  ✓ Se borraron todas las oraciones y átomos.")
            continue
        if not tokenizar(entrada):
            print("  ⚠ Escribe una oración para analizar.")
            continue

        registros.append(analizar(entrada, atomos, len(registros) + 1))
        mostrar_historial(registros)
        print("\n  Tip: escribe 'arbol' para ver el árbol semántico.")

    print("\nResumen final")
    mostrar_historial(registros)
    print("\n¡Hasta luego!")


if __name__ == "__main__":
    main()