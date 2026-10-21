#funcions_aux.py -- Càlculs físics i cerca eficient de veïns de la simulació.

import math
import time

K_PARET = 0.00
MU_VISCOSITAT = 1
RADI_INTERACCIO = 0.2
MIDA_CELLA = RADI_INTERACCIO

# Paràmetres del model SPH (unitats del model, no SI estrictes).
MASSA_PARTICULA = 0.01
DENSITAT_REPOS = 0
K_PRESSIO = 1
# K_PRESSIO gran --> Incompressible / K_PRESSIO petita --> Compressible.
# En realitat genera molta inestabilitat, ja que amb K grans has de fer el dt molt petit.
# dt <= RADI_INTERACCIO / K_PRESSIO


def construeix_graella(particules):
    graella = {}
    for particula in particules:
        clau = (int(particula.x // MIDA_CELLA), int(particula.y // MIDA_CELLA))
        graella.setdefault(clau, []).append(particula)
    return graella


def parelles_veines(graella):
    """Genera cada parella candidata una única vegada."""
    max_offset = math.ceil(RADI_INTERACCIO / MIDA_CELLA)
    for (cx, cy), cella in graella.items():
        for index, primera in enumerate(cella):
            for segona in cella[index + 1:]:
                yield primera, segona
        for ox in range(max_offset + 1):
            for oy in range(-max_offset, max_offset + 1):
                if ox == 0 and oy <= 0:
                    continue
                for primera in cella:
                    for segona in graella.get((cx + ox, cy + oy), []):
                        yield primera, segona


def forca_parets(particula, amplada_m, altura_m):
    esquerra = particula.x
    dreta = amplada_m - particula.x
    sostre = particula.y
    terra = altura_m - particula.y
    return (
        K_PARET / esquerra ** 2 - K_PARET / dreta ** 2,
        K_PARET / sostre ** 2 - K_PARET / terra ** 2,
    )


def geometria_parella(primera, segona):
    dx, dy = primera.x - segona.x, primera.y - segona.y
    distancia_quadrada = dx * dx + dy * dy
    if distancia_quadrada >= RADI_INTERACCIO ** 2:
        return None
    distancia = math.sqrt(distancia_quadrada)
    # Si dues partícules coincideixen, la direcció és indeterminada.
    # Escollim una direcció fixa perquè la força les pugui separar.
    if distancia == 0.0:
        ux, uy = 0.0, -1.0
    else:
        ux, uy = dx / distancia, dy / distancia
    return (distancia, ux, uy, primera.vx - segona.vx, primera.vy - segona.vy)


def kernel(r, h=RADI_INTERACCIO, d=2):
    """Kernel spline cúbic normalitzat en una o dues dimensions."""
    q = abs(r) / h
    if q <= 0.5:
        polinomi = 6 * (q ** 3 - q ** 2) + 1
    elif q < 1.0:
        polinomi = 2 * (1 - q) ** 3
    else:
        polinomi = 0.0
    sigma = 40 / (7 * math.pi * h ** 2) if d == 2 else 4 / (3 * h)
    return sigma * polinomi


def densitat_a_punt(particules, x, y, h=RADI_INTERACCIO):
    """Calcula la densitat SPH interpolada en un punt del pla."""
    densitat = 0.0
    for particula in particules:
        dx = particula.x - x
        dy = particula.y - y
        distancia = math.hypot(dx, dy)
        if distancia < h:
            densitat += MASSA_PARTICULA * kernel(distancia)
    return densitat


def gradient_kernel(r, h=RADI_INTERACCIO):
    """Gradient radial spiky per a la força de pressió en 2D.

    A diferència del kernel de densitat, la seva magnitud és màxima quan
    r tendeix a zero, cosa que evita que les partícules s'agrupin per manca
    de repulsió quan estan molt juntes.
    """
    if r >= h:
        return 0.0
    return -30 / (math.pi * h ** 5) * (h - r) ** 2


def calcula_interaccions(particules, amplada_m, altura_m, mesura_temps=False):
    inici = time.perf_counter() if mesura_temps else None
    for particula in particules:
        particula.ax, particula.ay = forca_parets(particula, amplada_m, altura_m)
    temps_parets = time.perf_counter() - inici if mesura_temps else 0.0

    inici = time.perf_counter() if mesura_temps else None
    graella = construeix_graella(particules)
    temps_graella = time.perf_counter() - inici if mesura_temps else 0.0

    inici = time.perf_counter() if mesura_temps else None
    candidates = efectives = 0

    # Primer pas SPH: densitat = suma de masses ponderades pel kernel.
    for particula in particules:
        particula.densitat = MASSA_PARTICULA * kernel(0.0)

    parelles = []
    for primera, segona in parelles_veines(graella):
        candidates += 1
        geometria = geometria_parella(primera, segona)
        if geometria is None:
            continue
        efectives += 1
        r, ux, uy, dvx, dvy = geometria
        pes_densitat = MASSA_PARTICULA * kernel(r)
        primera.densitat += pes_densitat
        segona.densitat += pes_densitat
        parelles.append((primera, segona, r, ux, uy, dvx, dvy))

    # Segon pas SPH: equació d'estat lineal.
    # Es limita a zero la pressió negativa per evitar inestabilitat de tracció
    # quan hi ha partícules aïllades o zones poc poblades.
    for particula in particules:
        # particula.pressio = K_PRESSIO * max( particula.densitat - DENSITAT_REPOS, 0.0)
        particula.pressio = K_PRESSIO * (particula.densitat - DENSITAT_REPOS)

    # Tercer pas: gradient de pressió + viscositat.
    for primera, segona, r, ux, uy, dvx, dvy in parelles:
        densitat_a = primera.densitat
        densitat_b = segona.densitat
        gradient = gradient_kernel(r)
        coeficient_pressio = -MASSA_PARTICULA * (
            primera.pressio / densitat_a ** 2
            + segona.pressio / densitat_b ** 2
        ) * gradient
        pes = 1 - r / RADI_INTERACCIO
        fx = coeficient_pressio * ux - MU_VISCOSITAT * pes * dvx
        fy = coeficient_pressio * uy - MU_VISCOSITAT * pes * dvy
        primera.ax += fx
        primera.ay += fy
        segona.ax -= fx
        segona.ay -= fy

    if not mesura_temps:
        return None
    return {
        "parets": temps_parets,
        "graella": temps_graella,
        "parelles": time.perf_counter() - inici,
        "candidates": candidates,
        "efectives": efectives,
        "cel·les": len(graella),
    }

