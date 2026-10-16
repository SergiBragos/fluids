#funcions_aux.py -- Càlculs físics i cerca eficient de veïns de la simulació.

import math
import time

K_REPULSIO = 0.02
DISTANCIA_MINIMA = 0.05
K_ATRACCIO = 0.02
K_PARET = 0.001
MU_VISCOSITAT = 1
RADI_INTERACCIO = 0.3
INV_R2_TALL = 1.0 / RADI_INTERACCIO ** 2
MIDA_CELLA = RADI_INTERACCIO / 2


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
    esquerra = max(particula.x, DISTANCIA_MINIMA)
    dreta = max(amplada_m - particula.x, DISTANCIA_MINIMA)
    sostre = max(particula.y, DISTANCIA_MINIMA)
    terra = max(altura_m - particula.y, DISTANCIA_MINIMA)
    return (
        K_PARET / esquerra ** 2 - K_PARET / dreta ** 2,
        K_PARET / sostre ** 2 - K_PARET / terra ** 2,
    )


def geometria_parella(primera, segona):
    dx, dy = primera.x - segona.x, primera.y - segona.y
    distancia_quadrada = dx * dx + dy * dy
    if distancia_quadrada >= RADI_INTERACCIO ** 2:
        return None
    distancia = max(math.sqrt(distancia_quadrada), DISTANCIA_MINIMA)
    return (distancia, dx / distancia, dy / distancia,
            primera.vx - segona.vx, primera.vy - segona.vy)


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
    for primera, segona in parelles_veines(graella):
        candidates += 1
        geometria = geometria_parella(primera, segona)
        if geometria is None:
            continue
        efectives += 1
        r, ux, uy, dvx, dvy = geometria
        repulsio = K_REPULSIO * (1 / r ** 2 - INV_R2_TALL)
        atraccio = -K_ATRACCIO * (1 - r / RADI_INTERACCIO)
        pes = 1 - r / RADI_INTERACCIO
        fx = (repulsio + atraccio) * ux - MU_VISCOSITAT * pes * dvx
        fy = (repulsio + atraccio) * uy - MU_VISCOSITAT * pes * dvy
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

def kernel(r, h, d = 2):
    q = abs(r)/h
    sigma_2D = 40/(7*math.pi*h*h)
    sigma_1D = 4/(3*h)
    if q <= 0.5:
        res = 6*(q*q*q - q*q) + 1
    elif q > 0.5 and q < 1:
        res = 2*(1 - q)**3
    else:
        res = 0
    if d == 2:
        return sigma_2D * res
    elif d == 1:
        return sigma_1D * res