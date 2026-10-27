"""
Sistemas Expertos - Identificador de conectores lógicos
Entrada de texto -> Tokenización -> Conectores -> Átomos -> Fórmula lógica
Cada oración digitada se guarda y se muestra en una tabla acumulada.
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

BICOND = ["si", "y", "solo", "si"]  # "si y solo si" son 4 palabras
LETRAS = "pqrstuvwxyz"
ANCHO_LINEA = 64


# ─────────────────────────── LÓGICA ───────────────────────────

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


def quitar_parentesis_externos(f):
    """Quita los paréntesis de afuera si envuelven toda la fórmula."""
    if f.startswith("(") and f.endswith(")"):
        nivel = 0
        for i, c in enumerate(f):
            nivel += (c == "(") - (c == ")")
            if nivel == 0 and i < len(f) - 1:
                return f
        return f[1:-1]
    return f


def parsear(tokens, atomos):
    """Traduce los tokens a una fórmula lógica (de menor a mayor precedencia:
    ↔, ⇒, Δ, ∨, ∧, ~) y registra los átomos (p, q, r...) en 'atomos'."""
    if not tokens:
        raise ValueError("Falta una proposición a un lado de un conector.")
    k = [sin_acentos(t) for t in tokens]

    # Bicondicional: p si y solo si q
    for i in range(len(k) - 3):
        if k[i:i + 4] == BICOND:
            izq = parsear(tokens[:i], atomos)
            der = parsear(tokens[i + 4:], atomos)
            return f"({izq} ↔ {der})"

    # Condicional: si p entonces q
    if k[0] == "si" and "entonces" in k:
        j = k.index("entonces")
        izq = parsear(tokens[1:j], atomos)
        der = parsear(tokens[j + 1:], atomos)
        return f"({izq} ⇒ {der})"

    # Disyunción exclusiva: o p o q
    if k[0] == "o" and "o" in k[1:]:
        j = k.index("o", 1)
        izq = parsear(tokens[1:j], atomos)
        der = parsear(tokens[j + 1:], atomos)
        return f"({izq} Δ {der})"

    # Disyunción: p o q
    if "o" in k:
        j = k.index("o")
        izq = parsear(tokens[:j], atomos)
        der = parsear(tokens[j + 1:], atomos)
        return f"({izq} ∨ {der})"

    # Conjunción: p y q
    if "y" in k:
        j = k.index("y")
        izq = parsear(tokens[:j], atomos)
        der = parsear(tokens[j + 1:], atomos)
        return f"({izq} ∧ {der})"

    # Negación: no p
    if k[0] == "no":
        return "~" + parsear(tokens[1:], atomos)

    # Átomo: proposición simple (misma frase = misma letra)
    frase = " ".join(tokens)
    if frase not in atomos:
        n = len(atomos)
        atomos[frase] = LETRAS[n] if n < len(LETRAS) else f"p{n}"
    return atomos[frase]


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
    print("  3. Detecta los conectores y la agrega a la tabla.")
    print()
    print(titulo("Conectores reconocidos"))
    for simbolo, operacion, _, significado in CONECTORES.values():
        print(f"  {simbolo:<2} {operacion:<22} {significado}")
    print()
    print(titulo("Comandos"))
    print("  historial  → ver la tabla acumulada")
    print("  ayuda      → ver estas instrucciones")
    print("  salir      → terminar el programa")
    print("─" * ANCHO_LINEA)


def imprimir_tabla(registros):
    """Dibuja la tabla acumulada. Cada registro es un dict con:
    'oracion' y 'filas' (lista de (operación, esquema, significado))."""
    encabezados = ["#", "Oración digitada", "Operación lógica", "Esquema", "Significado"]
    max_oracion = 34

    # Armar las filas: la oración y el # solo aparecen en la primera fila del grupo
    grupos = []
    for n, reg in enumerate(registros, start=1):
        grupo = []
        for i, (operacion, esquema, significado) in enumerate(reg["filas"]):
            if i == 0:
                oracion = textwrap.wrap(reg["oracion"], max_oracion) or [""]
                celdas = [[str(n)], oracion, [operacion], [esquema], [significado]]
            else:
                celdas = [[""], [""], [operacion], [esquema], [significado]]
            grupo.append(celdas)
        grupos.append(grupo)

    # Anchos de columna
    anchos = [len(h) for h in encabezados]
    for grupo in grupos:
        for celdas in grupo:
            for c, lineas in enumerate(celdas):
                anchos[c] = max(anchos[c], max(len(l) for l in lineas))

    def borde(izq, med, der):
        return izq + med.join("─" * (a + 2) for a in anchos) + der

    def fila(valores):
        return "│" + "│".join(f" {v:<{a}} " for v, a in zip(valores, anchos)) + "│"

    print(borde("┌", "┬", "┐"))
    print(fila(encabezados))
    for grupo in grupos:
        print(borde("├", "┼", "┤"))
        for celdas in grupo:
            alto = max(len(lineas) for lineas in celdas)
            for r in range(alto):
                print(fila([lineas[r] if r < len(lineas) else "" for lineas in celdas]))
    print(borde("└", "┴", "┘"))


def analizar(oracion):
    """Analiza una oración, muestra el resultado y devuelve el registro a guardar."""
    tokens = tokenizar(oracion)
    conectores, avisos = detectar_conectores(tokens)

    print()
    print(titulo("Análisis"))
    print("  Minúsculas :", oracion.lower())
    print("  Tokens     :", " | ".join(tokens))
    print("  Conectores :", ", ".join(f"«{t}»" for _, t, _ in conectores) or "ninguno")

    atomos = {}
    try:
        formula = quitar_parentesis_externos(parsear(tokens, atomos))
        for frase, letra in atomos.items():
            print(f"  Átomo {letra:<3}  : {frase}")
        print("  Fórmula    :", formula)
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

    return {"oracion": oracion.strip(), "filas": filas}


def mostrar_historial(registros):
    print()
    n = len(registros)
    print(titulo(f"Tabla acumulada ({n} {'oración' if n == 1 else 'oraciones'})"))
    if registros:
        imprimir_tabla(registros)
    else:
        print("  Aún no has digitado ninguna oración.")


def main():
    mostrar_bienvenida()
    registros = []  # aquí se guardan todas las oraciones digitadas

    while True:
        try:
            entrada = input(f"\nOración #{len(registros) + 1} ➜ ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        comando = entrada.lower()
        if comando == "salir":
            break
        if comando == "ayuda":
            mostrar_ayuda()
            continue
        if comando == "historial":
            mostrar_historial(registros)
            continue
        if not tokenizar(entrada):
            print("  ⚠ Escribe una oración para analizar.")
            continue

        registros.append(analizar(entrada))
        mostrar_historial(registros)

    print("\nResumen final")
    mostrar_historial(registros)
    print("\n¡Hasta luego!")


if __name__ == "__main__":
    main()