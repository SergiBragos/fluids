#simulacio.py

from particula import Particula
from funcions_aux import calcula_interaccions
import time
import math
import random
import pygame

# ============================================================
# CONFIGURACIÓ DE LES MESURES DE RENDIMENT
# ============================================================

MESURA_TEMPS = True       # False per desactivar les mesures
INTERVAL_IMPRESSIO = 60   # Imprimeix resultats cada 60 fotogrames

# ============================================================
# CONFIGURACIÓ DE LA FINESTRA
# ============================================================

AMPLADA, ALTURA = 400, 400
ALTURA_PANT = ALTURA + 30
FPS = 30

COLOR_FONS = (15, 15, 25)
COLOR_RECTANGLE = (80, 80, 80)
COLOR_QUIET = (80, 170, 255)
COLOR_RAPID = (255, 50, 50)

VELOCITAT_MAXIMA = 5.0
RADI = 5

# ============================================================
# FÍSICA GENERAL
# ============================================================

PIXELS_PER_METRE = 200.0
GRAVETAT = 0
RESTITUCIO = 0.5
NOMBRE_PARTICULES = 600

# Mides del recipient en metres.
AMPLADA_M = AMPLADA / PIXELS_PER_METRE
ALTURA_M = ALTURA / PIXELS_PER_METRE


# ============================================================
# EXECUCIÓ PRINCIPAL
# ============================================================

def main():
    pygame.init()

    pantalla = pygame.display.set_mode((AMPLADA, ALTURA_PANT))
    pygame.display.set_caption("Simulació de fluids")

    rellotge = pygame.time.Clock()
    font = pygame.font.Font(None, 24)

    particules = [
        Particula(
            random.uniform(RADI / PIXELS_PER_METRE, AMPLADA_M / 4),
            random.uniform(RADI / PIXELS_PER_METRE, ALTURA_M - RADI / PIXELS_PER_METRE),
            RADI
        )
        for _ in range(NOMBRE_PARTICULES)
    ]

    executant = True

    # Acumuladors de mesures.
    mostres = 0

    acumulats = {
        "parets": 0.0,
        "graella": 0.0,
        "parelles": 0.0,
        "actualitzacio": 0.0,
        "dibuix": 0.0,
        "fotograma": 0.0,
        "candidates": 0,
        "efectives": 0,
        "cel·les": 0
    }

    while executant:
        dt = rellotge.tick(FPS) / 1000.0
        dt = min(dt, 1 / 30)

        # El temps de processament no inclou l'espera de rellotge.tick().
        if MESURA_TEMPS:
            inici_fotograma = time.perf_counter()

        for esdeveniment in pygame.event.get():
            if esdeveniment.type == pygame.QUIT:
                executant = False

            elif (
                esdeveniment.type == pygame.KEYDOWN
                and esdeveniment.key == pygame.K_ESCAPE
            ):
                executant = False

        if not executant:
            break

        # 1. Interaccions.
        mesures = calcula_interaccions(
            particules, AMPLADA_M, ALTURA_M, MESURA_TEMPS
        )

        # 2. Actualització física.
        if MESURA_TEMPS:
            t0 = time.perf_counter()

        v_mitjana = 0.0

        for particula in particules:
            particula.actualitza(
                dt, GRAVETAT, RESTITUCIO,
                AMPLADA_M, ALTURA_M, PIXELS_PER_METRE,
            )
            v_mitjana += math.hypot(particula.vx, particula.vy)

        v_mitjana /= len(particules)

        if MESURA_TEMPS:
            temps_actualitzacio = time.perf_counter() - t0

        # 3. Dibuix.
        if MESURA_TEMPS:
            t0 = time.perf_counter()

        pantalla.fill(COLOR_FONS)

        for particula in particules:
            particula.dibuixa(
                pantalla, PIXELS_PER_METRE, VELOCITAT_MAXIMA,
                COLOR_QUIET, COLOR_RAPID,
            )

        t = min(v_mitjana / VELOCITAT_MAXIMA, 1.0)

        color_text = tuple(
            int(a + t * (b - a))
            for a, b in zip(COLOR_QUIET, COLOR_RAPID)
        )

        text_velocitat = font.render(
            f"v mitjana: {v_mitjana:.2f} m/s",
            True,
            color_text
        )

        pygame.draw.rect(
            pantalla,
            COLOR_RECTANGLE,
            (0, ALTURA, AMPLADA, ALTURA_PANT - ALTURA)
        )

        pantalla.blit(
            text_velocitat,
            text_velocitat.get_rect(
                topright=(AMPLADA - 10, ALTURA_PANT - 25)
            )
        )

        pygame.display.flip()

        if MESURA_TEMPS:
            temps_dibuix = time.perf_counter() - t0
            temps_fotograma = time.perf_counter() - inici_fotograma

            acumulats["parets"] += mesures["parets"]
            acumulats["graella"] += mesures["graella"]
            acumulats["parelles"] += mesures["parelles"]
            acumulats["actualitzacio"] += temps_actualitzacio
            acumulats["dibuix"] += temps_dibuix
            acumulats["fotograma"] += temps_fotograma

            acumulats["candidates"] += mesures["candidates"]
            acumulats["efectives"] += mesures["efectives"]
            acumulats["cel·les"] += mesures["cel·les"]

            mostres += 1

            # Imprimeix les mitjanes de l'interval.
            if mostres >= INTERVAL_IMPRESSIO:
                factor_ms = 1000.0 / mostres

                print(
                    f"\n--- Mitjanes dels últims {mostres} fotogrames ---"
                )
                print(
                    f"Forces de paret:       "
                    f"{acumulats['parets'] * factor_ms:.3f} ms"
                )
                print(
                    f"Construcció graella:   "
                    f"{acumulats['graella'] * factor_ms:.3f} ms"
                )
                print(
                    f"Parelles i forces:     "
                    f"{acumulats['parelles'] * factor_ms:.3f} ms"
                )
                print(
                    f"Actualització física:  "
                    f"{acumulats['actualitzacio'] * factor_ms:.3f} ms"
                )
                print(
                    f"Dibuix:                "
                    f"{acumulats['dibuix'] * factor_ms:.3f} ms"
                )
                print(
                    f"Processament fotograma:"
                    f" {acumulats['fotograma'] * factor_ms:.3f} ms"
                )
                print(
                    f"Cel·les ocupades:      "
                    f"{acumulats['cel·les'] / mostres:.1f}"
                )
                print(
                    f"Parelles candidates:   "
                    f"{acumulats['candidates'] / mostres:.1f}"
                )
                print(
                    f"Parelles efectives:    "
                    f"{acumulats['efectives'] / mostres:.1f}"
                )

                # Reinicia els acumuladors.
                for clau in acumulats:
                    acumulats[clau] = 0

                mostres = 0

    pygame.quit()


if __name__ == "__main__":
    main()
