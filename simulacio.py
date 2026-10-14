"""
Pas 1: finestra de pygame amb una partícula afectada per la gravetat.

Dependències:  pip install pygame
Execució:      python simulacio.py
"""

import pygame
import random

# --- Configuració de la finestra ---
AMPLADA, ALTURA = 400, 300
FPS = 30
COLOR_FONS = (15, 15, 25)
COLOR_PARTICULA = (80, 170, 255)

# --- Física ---
PIXELS_PER_METRE = 100.0        # escala: 100 px = 1 m
GRAVETAT = 9.81                # m/s^2 (positiu = cap avall)
RESTITUCIO = 0.5                # 1 = rebot perfecte, 0 = no rebota
COLOR_QUIET = (80, 170, 255)      # blau
COLOR_RAPID = (255, 50, 50)       # vermell
VELOCITAT_MAXIMA = 8.0            # m/s a partir de la qual ja és ben vermella
K_REPULSIO = 0.03          # intensitat (a = K / r^2, amb massa 1 i r en metres)
K_PARET = 0.03             # intensitat particula-paret
DISTANCIA_MINIMA = 0.05   # m; evita la força infinita quan dues partícules es toquen
MU_VISCOSITAT = 1        # 1/s; intensitat de la fricció entre veïnes
RADI_VISCOSITAT = 0.2      # m; només interactuen si estan més a prop que això

NOMBRE_PARTICULES = 300

class Particula:
    def __init__(self, x, y, radi=5):
        # posició i velocitat en metres (la y creix cap avall, com a pygame)
        self.x = x / PIXELS_PER_METRE
        self.y = y / PIXELS_PER_METRE
        self.vx = 0.0
        self.vy = 0.0
        self.ax = 0.0          # acceleració deguda a les altres partícules
        self.ay = 0.0
        self.radi = radi

    def actualitza(self, dt):
        # Euler semi-implícit: primer la velocitat, després la posició
        self.vx += self.ax * dt
        self.vy += (GRAVETAT + self.ay) * dt
        self.x += self.vx * dt
        self.y += self.vy * dt

        # terra: rebota (així la partícula no desapareix de la pantalla)
        terra = (ALTURA - self.radi) / PIXELS_PER_METRE
        paret_dreta = (AMPLADA - self.radi) / PIXELS_PER_METRE
        paret_esquerra = self.radi / PIXELS_PER_METRE
        if self.y > terra:
            self.y = terra #- 1/PIXELS_PER_METRE
            self.vy = -self.vy * RESTITUCIO
        if self.y < 0:
            self.y = 0 #+ 1/PIXELS_PER_METRE
            self.vy = -self.vy * RESTITUCIO
        if self.x > paret_dreta:
            self.x = paret_dreta #- 1/PIXELS_PER_METRE
            self.vx = -self.vx * RESTITUCIO
        if self.x < paret_esquerra:
            self.x = paret_esquerra #+ 1/PIXELS_PER_METRE
            self.vx = -self.vx * RESTITUCIO    

    def color(self):
        vel = (self.vx**2 + self.vy**2) ** 0.5
        t = min(vel / VELOCITAT_MAXIMA, 1.0)      # 0 = quieta, 1 = molt ràpida
        return tuple(int(a + t * (b - a)) for a, b in zip(COLOR_QUIET, COLOR_RAPID))

    def dibuixa(self, pantalla):
        pos = (int(self.x * PIXELS_PER_METRE), int(self.y * PIXELS_PER_METRE))
        pygame.draw.circle(pantalla, self.color(), pos, self.radi)

    def repulsio_parets(self):
        w, h = AMPLADA / PIXELS_PER_METRE, ALTURA / PIXELS_PER_METRE
        d_esq = max(self.x, DISTANCIA_MINIMA)
        d_dre = max(w - self.x, DISTANCIA_MINIMA)
        d_sos = max(self.y, DISTANCIA_MINIMA)
        d_ter = max(h - self.y, DISTANCIA_MINIMA)
        self.ax += K_PARET / d_esq**2 - K_PARET / d_dre**2
        self.ay += K_PARET / d_sos**2 - K_PARET / d_ter**2

#Funcions auxiliars
def calcula_interaccions(particules):
    for p in particules:
        p.ax = 0.0
        p.ay = 0.0
        p.repulsio_parets()
        
    for i in range(len(particules)):
        for j in range(i + 1, len(particules)):   # cada parella una sola vegada
            a, b = particules[i], particules[j]
            dx = a.x - b.x
            dy = a.y - b.y
            r2 = max(dx * dx + dy * dy, DISTANCIA_MINIMA ** 2)
            r = r2 ** 0.5
            f = K_REPULSIO / r2                    # magnitud (massa = 1)
            fx, fy = f * dx / r, f * dy / r        # direcció: de b cap a a
            a.ax += fx
            a.ay += fy
            b.ax -= fx                             # tercera llei de Newton
            b.ay -= fy
            
            if r < RADI_VISCOSITAT:
                w = 1 - r / RADI_VISCOSITAT          # 1 si es toquen, 0 al límit del radi
                dvx = a.vx - b.vx
                dvy = a.vy - b.vy
                a.ax -= MU_VISCOSITAT * w * dvx      # cada una frena la velocitat relativa
                a.ay -= MU_VISCOSITAT * w * dvy
                b.ax += MU_VISCOSITAT * w * dvx
                b.ay += MU_VISCOSITAT * w * dvy
#-----FI DE CÀLCUL D'INTERACCIONS-----#


#Execució del programa
def main():
    pygame.init()
    pantalla = pygame.display.set_mode((AMPLADA, ALTURA))
    pygame.display.set_caption("Simulació de fluids - pas 1")
    rellotge = pygame.time.Clock()

    particules = []
    for i in range(0, NOMBRE_PARTICULES):
        particula = Particula(random.randint(0, AMPLADA), random.randint(0, ALTURA))
        particules.append(particula)

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

        pantalla.fill(COLOR_FONS)          # el fons es pinta una sola vegada, abans de dibuixar
        for particula in particules:
            particula.dibuixa(pantalla)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()