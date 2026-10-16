#particula.py -- Classe que representa una partícula de la simulació.

import math
import pygame

class Particula:
    """Estat i comportament d'una única partícula."""

    def __init__(self, x, y, radi=5):
        self.x, self.y, self.radi = x, y, radi
        self.vx = self.vy = 0.0
        self.ax = self.ay = 0.0

    def actualitza(self, dt, gravetat, restitucio, amplada_m, altura_m, pixels_per_metre):
        """Integra el moviment i limita la partícula al recipient."""
        self.vx += self.ax * dt
        self.vy += (gravetat + self.ay) * dt
        self.x += self.vx * dt
        self.y += self.vy * dt

        radi_m = self.radi / pixels_per_metre
        paret_dreta = amplada_m - radi_m
        terra = altura_m - radi_m
        if self.y >= terra:
            self.y, self.vy = terra, -self.vy * restitucio
        elif self.y <= radi_m:
            self.y, self.vy = radi_m, -self.vy * restitucio
        if self.x >= paret_dreta:
            self.x, self.vx = paret_dreta, -self.vx * restitucio
        elif self.x <= radi_m:
            self.x, self.vx = radi_m, -self.vx * restitucio

    def dibuixa(self, pantalla, pixels_per_metre, velocitat_maxima, color_quiet, color_rapid):
        velocitat = math.hypot(self.vx, self.vy)
        proporcio = min(velocitat / velocitat_maxima, 1.0)
        color = tuple(
            int(inicial + proporcio * (final - inicial))
            for inicial, final in zip(color_quiet, color_rapid)
        )
        posicio = (int(self.x * pixels_per_metre), int(self.y * pixels_per_metre))
        pygame.draw.circle(pantalla, color, posicio, self.radi)

