"""
Simulació 2D de partícules amb gravetat i interaccions (pygame).

Cada interacció viu en la seva pròpia funció:
  - forca_repulsio   : repulsió entre partícules (1/r^2)
  - forca_atraccio   : atracció feble i de curt abast entre partícules
  - forca_parets     : repulsió de les parets del recipient
  - forca_viscosa    : fricció entre partícules veïnes

Dependències:  pip install pygame   (o pygame-ce amb Python 3.14)
Execució:      python simulacio.py
"""

import math
import random
import pygame

# --- Configuració de la finestra ---
AMPLADA, ALTURA = 400, 300
FPS = 30
COLOR_FONS = (15, 15, 25)
COLOR_QUIET = (80, 170, 255)      # blau
COLOR_RAPID = (255, 50, 50)       # vermell
VELOCITAT_MAXIMA = 8.0            # m/s a partir de la qual ja és ben vermella

# --- Física general ---
PIXELS_PER_METRE = 100.0          # escala: 100 px = 1 m
GRAVETAT = 9.81                   # m/s^2 (positiu = cap avall)
RESTITUCIO = 0.3                  # 1 = rebot perfecte, 0 = no rebota
NOMBRE_PARTICULES = 300

# --- Paràmetres de cada interacció ---
#Repulsió inv. quadràtica
K_REPULSIO = 0.03                 # a = K / r^2 (massa 1, r en metres)
DISTANCIA_MINIMA = 0.05           # m; evita forces infinites quan dues partícules es toquen
#Atracció lineal
K_ATRACCIO = 0.5                  # m/s^2 quan r -> 0 (cau linealment fins a 0 a RADI_ATRACCIO)
RADI_ATRACCIO = 0.1               # m; abast de l'atracció
# Amb aquests valors la repulsió i l'atracció s'igualen a r ~ ? m (distància d'equilibri)
K_PARET = 0.03                    # intensitat partícula-paret
#Viscositat
MU_VISCOSITAT = 3.0               # 1/s; intensitat de la fricció entre veïnes
RADI_VISCOSITAT = 0.1             # m; només interactuen si estan més a prop que això

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
    """Repulsió entre partícules, inversament proporcional a r^2."""
    f = K_REPULSIO / (r * r)
    return f * ux, f * uy


def forca_atraccio(r, ux, uy):
    """Atracció feble: màxima a r = 0 i nul·la a partir de RADI_ATRACCIO."""
    if r >= RADI_ATRACCIO:
        return 0.0, 0.0
    f = -K_ATRACCIO * (1 - r / RADI_ATRACCIO)    # signe negatiu = cap a b
    return f * ux, f * uy


def forca_viscosa(r, dvx, dvy):
    """Fricció que frena la velocitat relativa entre veïnes."""
    if r >= RADI_VISCOSITAT:
        return 0.0, 0.0
    w = 1 - r / RADI_VISCOSITAT                  # 1 si es toquen, 0 al límit del radi
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
    """Calcula una sola vegada tot el que necessiten les funcions de parella."""
    dx = a.x - b.x
    dy = a.y - b.y
    r = max(math.hypot(dx, dy), DISTANCIA_MINIMA)
    return r, dx / r, dy / r, a.vx - b.vx, a.vy - b.vy


def calcula_interaccions(particules):
    """Només suma els efectes de cada interacció sobre l'acceleració."""
    for p in particules:
        p.ax, p.ay = forca_parets(p)

    n = len(particules)
    for i in range(n):
        for j in range(i + 1, n):                # cada parella una sola vegada
            a, b = particules[i], particules[j]
            r, ux, uy, dvx, dvy = geometria_parella(a, b)

            rep = forca_repulsio(r, ux, uy)
            atr = forca_atraccio(r, ux, uy)
            vis = forca_viscosa(r, dvx, dvy)

            fx = rep[0] + atr[0] + vis[0]
            fy = rep[1] + atr[1] + vis[1]
            a.ax += fx
            a.ay += fy
            b.ax -= fx
            b.ay -= fy


# ======================================================================
#  EXECUCIÓ
# ======================================================================

def main():
    pygame.init()
    pantalla = pygame.display.set_mode((AMPLADA, ALTURA))
    pygame.display.set_caption("Simulació de fluids")
    rellotge = pygame.time.Clock()

    particules = [
        Particula(random.randint(0, AMPLADA), random.randint(0, ALTURA))
        for _ in range(NOMBRE_PARTICULES)
    ]

    executant = True
    while executant:
        dt = rellotge.tick(FPS) / 1000.0   # segons des de l'últim fotograma
        dt = min(dt, 1 / 30)               # evita salts grans si la finestra es bloqueja

        for esdeveniment in pygame.event.get():
            if esdeveniment.type == pygame.QUIT:
                executant = False
            elif esdeveniment.type == pygame.KEYDOWN and esdeveniment.key == pygame.K_ESCAPE:
                executant = False

        calcula_interaccions(particules)
        for particula in particules:
            particula.actualitza(dt)

        pantalla.fill(COLOR_FONS)
        for particula in particules:
            particula.dibuixa(pantalla)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()