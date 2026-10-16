"""
Simulació 2D de partícules amb gravetat i interaccions (pygame).

Cada interacció viu en la seva pròpia funció:
  - forca_repulsio   : repulsió entre partícules (1/r^2)
  - forca_atraccio   : atracció feble i de curt abast entre partícules
  - forca_parets     : repulsió de les parets del recipient
  - forca_viscosa    : fricció entre partícules veïnes

Optimització: totes les forces entre partícules tenen un abast finit
(RADI_INTERACCIO) i només es calculen entre partícules de cel·les veïnes d'una
graella, de manera que el cost creix com N i no com N^2.

Dependències:  pip install pygame   (o pygame-ce amb Python 3.14)
Execució:      python simulacio.py
"""

import time
import math
import random
import pygame

# --- Configuració de la finestra ---
AMPLADA, ALTURA = 600, 400
ALTURA_PANT = ALTURA + 30
FPS = 30
COLOR_FONS = (15, 15, 25)
COLOR_RECTANGLE = (80, 80, 80)
COLOR_QUIET = (80, 170, 255)      # blau
COLOR_RAPID = (255, 50, 50)       # vermell
VELOCITAT_MAXIMA = 5.0            # m/s a partir de la qual ja és ben vermella
RADI = 6

# --- Física general ---
PIXELS_PER_METRE = 200.0          # escala: 100 px = 1 m
GRAVETAT = 9.81                   # m/s^2 (positiu = cap avall)
RESTITUCIO = 0.5                  # 1 = rebot perfecte, 0 = no rebota
NOMBRE_PARTICULES = 600

# --- Paràmetres de cada interacció ---
K_REPULSIO = 0.01                 # a = K * (1/r^2 - 1/R^2), amb R = RADI_INTERACCIO (massa 1, r en m)
DISTANCIA_MINIMA = 0.05           # m; evita forces infinites quan dues partícules es toquen

K_ATRACCIO = 0.05                  # m/s^2 quan r -> 0 (cau linealment fins a 0 a RADI_ATRACCIO)

K_PARET = 0.003                    # intensitat partícula-paret

MU_VISCOSITAT = 0.1               # 1/s; intensitat de la fricció entre veïnes

# Abast màxim de qualsevol interacció entre partícules; també és la mida de cel·la de la graella
RADI_INTERACCIO = 0.3
INV_R2_TALL = 1.0 / RADI_INTERACCIO ** 2
# Amb aquests valors la repulsió i l'atracció s'igualen a r ~ 0.15 m (distància d'equilibri)

# Mides del recipient en metres (es calculen una sola vegada)
AMPLADA_M = AMPLADA / PIXELS_PER_METRE
ALTURA_M = ALTURA / PIXELS_PER_METRE


class Particula:
    def __init__(self, x, y, radi=5):
        # posició i velocitat en metres (la y creix cap avall, com a pygame)
        self.x = x / PIXELS_PER_METRE
        self.y = y / PIXELS_PER_METRE
        self.vx = 0.0
        self.vy = 0.0
        self.ax = 0.0             # acceleració deguda a les interaccions
        self.ay = 0.0
        self.radi = radi

    def actualitza(self, dt):
        # Euler semi-implícit: primer la velocitat, després la posició
        self.vx += self.ax * dt
        self.vy += (GRAVETAT + self.ay) * dt
        self.x += self.vx * dt
        self.y += self.vy * dt

        # xarxa de seguretat: si una partícula toca la paret, rebota
        terra = (ALTURA - self.radi) / PIXELS_PER_METRE
        paret_dreta = (AMPLADA - self.radi) / PIXELS_PER_METRE
        paret_esquerra = self.radi / PIXELS_PER_METRE
        if self.y > terra:
            self.y = terra
            self.vy = -self.vy * RESTITUCIO
        if self.y < 0:
            self.y = 0
            self.vy = -self.vy * RESTITUCIO
        if self.x > paret_dreta:
            self.x = paret_dreta
            self.vx = -self.vx * RESTITUCIO
        if self.x < paret_esquerra:
            self.x = paret_esquerra
            self.vx = -self.vx * RESTITUCIO

    def color(self):
        vel = math.hypot(self.vx, self.vy)
        t = min(vel / VELOCITAT_MAXIMA, 1.0)      # 0 = quieta, 1 = molt ràpida
        return tuple(int(a + t * (b - a)) for a, b in zip(COLOR_QUIET, COLOR_RAPID))

    def dibuixa(self, pantalla):
        pos = (int(self.x * PIXELS_PER_METRE), int(self.y * PIXELS_PER_METRE))
        pygame.draw.circle(pantalla, self.color(), pos, self.radi)


# ======================================================================
#  INTERACCIONS
#  Les funcions de parella retornen la força (fx, fy) que rep la partícula
#  "a"; la partícula "b" rep l'oposada (tercera llei de Newton).
#  r = distància, (ux, uy) = vector unitari de b cap a a,
#  (dvx, dvy) = velocitat de a respecte de b.
# ======================================================================

def forca_repulsio(r, ux, uy):
    """Repulsió ~1/r^2, desplaçada perquè sigui exactament 0 a RADI_INTERACCIO
    (si es tallés de cop, la força faria un salt i generaria soroll)."""
    f = K_REPULSIO * (1.0 / (r * r) - INV_R2_TALL)
    return f * ux, f * uy


def forca_atraccio(r, ux, uy):
    """Atracció feble: màxima a r = 0 i nul·la a partir de RADI_ATRACCIO."""
    if r >= RADI_INTERACCIO:
        return 0.0, 0.0
    f = -K_ATRACCIO * (1 - r / RADI_INTERACCIO)    # signe negatiu = cap a b
    return f * ux, f * uy


def forca_viscosa(r, dvx, dvy):
    """Fricció que frena la velocitat relativa entre veïnes."""
    if r >= RADI_INTERACCIO:
        return 0.0, 0.0
    w = 1 - r / RADI_INTERACCIO                  # 1 si es toquen, 0 al límit del radi
    return -MU_VISCOSITAT * w * dvx, -MU_VISCOSITAT * w * dvy


def forca_parets(p):
    """Repulsió de les quatre parets sobre una partícula (acceleració ax, ay)."""
    d_esq = max(p.x, DISTANCIA_MINIMA)
    d_dre = max(AMPLADA_M - p.x, DISTANCIA_MINIMA)
    d_sos = max(p.y, DISTANCIA_MINIMA)
    d_ter = max(ALTURA_M - p.y, DISTANCIA_MINIMA)
    ax = K_PARET / d_esq ** 2 - K_PARET / d_dre ** 2
    ay = K_PARET / d_sos ** 2 - K_PARET / d_ter ** 2
    return ax, ay


def geometria_parella(a, b):
    """Calcula una sola vegada tot el que necessiten les funcions de parella.
    Retorna None si la parella és fora de l'abast de les interaccions."""
    dx = a.x - b.x
    dy = a.y - b.y
    d2 = dx * dx + dy * dy
    if d2 >= RADI_INTERACCIO ** 2:
        return None
    r = max(math.sqrt(d2), DISTANCIA_MINIMA)
    return r, dx / r, dy / r, a.vx - b.vx, a.vy - b.vy


def construeix_graella(particules):
    """Reparteix les partícules en cel·les quadrades de costat RADI_INTERACCIO."""
    graella = {}
    for p in particules:
        clau = (int(p.x // RADI_INTERACCIO), int(p.y // RADI_INTERACCIO))
        graella.setdefault(clau, []).append(p)
    return graella


def parelles_veines(graella):
    """Genera cada parella de partícules que podrien interaccionar, una sola vegada.
    Una partícula només pot tenir veïnes dins de la seva cel·la o de les 8 de
    voltant; per no repetir parelles, cada cel·la només mira la seva i 4 de veïnes."""
    for (cx, cy), cella in graella.items():
        n = len(cella)
        for i in range(n):                       # parelles dins la mateixa cel·la
            for j in range(i + 1, n):
                yield cella[i], cella[j]
        for ox, oy in ((1, 0), (-1, 1), (0, 1), (1, 1)):
            altra = graella.get((cx + ox, cy + oy))
            if altra:
                for a in cella:
                    for b in altra:
                        yield a, b



def calcula_interaccions(particules):
    inici = time.perf_counter()

    for p in particules:
        p.ax, p.ay = forca_parets(p)

    t_parets = time.perf_counter()
    graella = construeix_graella(particules)
    t_graella = time.perf_counter()

    candidates = 0
    efectives = 0

    for a, b in parelles_veines(graella):
        candidates += 1

        geo = geometria_parella(a, b)
        if geo is None:
            continue

        efectives += 1
        r, ux, uy, dvx, dvy = geo

        rep = forca_repulsio(r, ux, uy)
        atr = forca_atraccio(r, ux, uy)
        vis = forca_viscosa(r, dvx, dvy)

        fx = rep[0] + atr[0] + vis[0]
        fy = rep[1] + atr[1] + vis[1]
        a.ax += fx
        a.ay += fy
        b.ax -= fx
        b.ay -= fy

    final = time.perf_counter()

    # Acumula les mesures i informa cada 30 crides.
    if not hasattr(calcula_interaccions, "_mostres"):
        calcula_interaccions._mostres = []

    calcula_interaccions._mostres.append((
        (t_parets - inici) * 1000,
        (t_graella - t_parets) * 1000,
        (final - t_graella) * 1000,
        candidates,
        efectives,
    ))

    if len(calcula_interaccions._mostres) >= 30:
        dades = calcula_interaccions._mostres
        n = len(dades)

        print(
            f"Parets: {sum(d[0] for d in dades) / n:.2f} ms | "
            f"Graella: {sum(d[1] for d in dades) / n:.2f} ms | "
            f"Parelles: {sum(d[2] for d in dades) / n:.2f} ms | "
            f"Candidats/fotograma: "
            f"{sum(d[3] for d in dades) / n:.0f} | "
            f"Interaccions/fotograma: "
            f"{sum(d[4] for d in dades) / n:.0f}"
        )

        calcula_interaccions._mostres = []


# ======================================================================
#  EXECUCIÓ
# ======================================================================
def main():
    pygame.init()
    pantalla = pygame.display.set_mode((AMPLADA, ALTURA_PANT))
    pygame.draw.rect(pantalla, COLOR_RECTANGLE, (100, 100, 100, 100))
    pygame.display.set_caption("Simulació de fluids")
    rellotge = pygame.time.Clock()
    font = pygame.font.Font(None, 24)      # tipus de lletra per defecte de pygame

    particules = [
        Particula(random.randint(0, AMPLADA//4), random.randint(0, ALTURA), RADI)
        for _ in range(NOMBRE_PARTICULES)
    ]

    ultim_informe = time.perf_counter()
    fotogrames = 0
    suma_interaccions = 0.0
    suma_actualitzacio = 0.0
    suma_dibuix = 0.0
    executant = True

    while executant:
        dt = rellotge.tick(FPS) / 1000.0   # segons des de l'últim fotograma
        dt = min(dt, 1 / 30)               # evita salts grans si la finestra es bloqueja

        for esdeveniment in pygame.event.get():
            if esdeveniment.type == pygame.QUIT:
                executant = False
            elif esdeveniment.type == pygame.KEYDOWN and esdeveniment.key == pygame.K_ESCAPE:
                executant = False
        
        # 1. Interaccions entre partícules
        t0 = time.perf_counter()
        calcula_interaccions(particules)
        t_interaccions = time.perf_counter() - t0

        # 2. Actualització física
        t0 = time.perf_counter()
        for particula in particules:
            particula.actualitza(dt)
        t_actualitzacio = time.perf_counter() - t0

        v_mitjana = sum(
            math.hypot(p.vx, p.vy) for p in particules
        ) / len(particules)

        # 3. Dibuix de les partícules
        t0 = time.perf_counter()
        pantalla.fill(COLOR_FONS)
        for particula in particules:
            particula.dibuixa(pantalla)

        t = min(v_mitjana / VELOCITAT_MAXIMA, 1.0)      # 0 = quieta, 1 = molt ràpida
        text = font.render(f"v mitjana: {v_mitjana:.2f} m/s", True, tuple(int(a + t * (b - a)) for a, b in zip(COLOR_QUIET, COLOR_RAPID)))
        pygame.draw.rect(pantalla, COLOR_RECTANGLE, (0, ALTURA, AMPLADA, ALTURA_PANT-ALTURA))
        pantalla.blit(text, text.get_rect(topright=(AMPLADA - 10, ALTURA_PANT - 25)))

        pygame.display.flip()
        t_dibuix = time.perf_counter() - t0
        fotogrames += 1
        suma_interaccions += t_interaccions
        suma_actualitzacio += t_actualitzacio
        suma_dibuix += t_dibuix

        ara = time.perf_counter()
        if ara - ultim_informe >= 1.0:
            n = max(fotogrames, 1)

            """
            print(
                f"Partícules: {len(particules)} | "
                f"FPS objectiu: {FPS} | "
                f"Interaccions: {suma_interaccions / n * 1000:.2f} ms | "
                f"Actualització: {suma_actualitzacio / n * 1000:.2f} ms | "
                f"Dibuix: {suma_dibuix / n * 1000:.2f} ms"
            )

            ultim_informe = ara
            fotogrames = 0
            suma_interaccions = 0.0
            suma_actualitzacio = 0.0
            suma_dibuix = 0.0
            """

    pygame.quit()

if __name__ == "__main__":
    main()
