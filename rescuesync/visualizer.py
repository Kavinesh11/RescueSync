"""Pygame demo (see README for the primary web UI). Controls:

Space: play/pause    Right arrow: step one timestep
1 / 2 / 3: switch mode (re-plans the same scenario)    R: restart
"""
from __future__ import annotations

CELL_SIZE = 36

WALL_COLOR = (55, 58, 64)
FLOOR_COLOR = (238, 238, 235)
RUBBLE_COLOR = (140, 94, 62)
RUBBLE_CLEARED_COLOR = (214, 186, 150)
VICTIM_COLOR = (214, 64, 69)
ENGINEER_COLOR = (240, 152, 25)
MEDIC_COLOR = (43, 108, 196)
COLLISION_COLOR = (220, 20, 20)
TEXT_COLOR = (20, 20, 20)
PANEL_BG = (250, 250, 248)


def run_visualizer(scenario: dict, initial_mode) -> None:
    import pygame

    from .environment import Grid
    from .metrics import compute_metrics
    from .planner import Mode, plan_all
    from .simulator import simulate

    pygame.init()
    grid = Grid.from_scenario(scenario)
    panel_w = 260
    screen = pygame.display.set_mode((grid.width * CELL_SIZE + panel_w, grid.height * CELL_SIZE))
    pygame.display.set_caption("RescueSync")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 16)
    big_font = pygame.font.SysFont("consolas", 20, bold=True)

    mode = initial_mode

    def do_plan(m):
        result = plan_all(scenario, m)
        metrics = compute_metrics(result)
        sim = simulate(result)
        collisions_by_t = {}
        for c in sim["collisions"]:
            collisions_by_t.setdefault(c["t"], []).append(c)
        return result, metrics, collisions_by_t

    result, metrics, collisions_by_t = do_plan(mode)
    t = 0
    playing = False
    max_t = max((len(a.schedule) - 1 for a in result.agents.values() if a.schedule), default=0)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    playing = not playing
                elif event.key == pygame.K_RIGHT:
                    t = min(t + 1, max_t)
                elif event.key == pygame.K_LEFT:
                    t = max(t - 1, 0)
                elif event.key == pygame.K_r:
                    t = 0
                    playing = False
                elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                    mode = {pygame.K_1: Mode.INDEPENDENT, pygame.K_2: Mode.COOPERATIVE, pygame.K_3: Mode.RESCUESYNC}[event.key]
                    result, metrics, collisions_by_t = do_plan(mode)
                    t = 0
                    max_t = max((len(a.schedule) - 1 for a in result.agents.values() if a.schedule), default=0)

        if playing:
            t = min(t + 1, max_t)
            if t == max_t:
                playing = False

        screen.fill(PANEL_BG)
        for r in range(grid.height):
            for c in range(grid.width):
                cell = (r, c)
                if cell in grid.walls:
                    color = WALL_COLOR
                elif cell in grid.rubble:
                    color = RUBBLE_CLEARED_COLOR if t >= result.open_time.get(cell, float("inf")) else RUBBLE_COLOR
                elif cell in grid.victims:
                    color = VICTIM_COLOR
                else:
                    color = FLOOR_COLOR
                pygame.draw.rect(screen, color, (c * CELL_SIZE, r * CELL_SIZE, CELL_SIZE - 1, CELL_SIZE - 1))

        collided_agents = set()
        for c in collisions_by_t.get(t, []):
            collided_agents.update(c["agents"])

        for aid, agent in result.agents.items():
            if not agent.schedule:
                continue
            pos = agent.schedule[min(t, len(agent.schedule) - 1)]
            cx = pos[1] * CELL_SIZE + CELL_SIZE // 2
            cy = pos[0] * CELL_SIZE + CELL_SIZE // 2
            base_color = ENGINEER_COLOR if agent.role == "engineer" else MEDIC_COLOR
            color = COLLISION_COLOR if aid in collided_agents else base_color
            pygame.draw.circle(screen, color, (cx, cy), CELL_SIZE // 2 - 4)
            label = font.render(aid, True, (255, 255, 255))
            screen.blit(label, (cx - label.get_width() // 2, cy - label.get_height() // 2))

        panel_x = grid.width * CELL_SIZE + 12
        lines = [
            f"Mode: {mode.value}",
            f"t = {t} / {max_t}",
            "",
            f"Rescued: {metrics['victims_rescued']}/{metrics['victims_total']}",
            f"Collisions: {metrics['collisions']}",
            f"Makespan: {metrics['makespan']}",
            f"Waits: {metrics['wait_actions']}",
            f"Planning: {metrics['planning_time_ms']} ms",
            "",
            "Space: play/pause",
            "Right: step",
            "1/2/3: switch mode",
            "R: restart",
        ]
        for i, line in enumerate(lines):
            surf = big_font.render(line, True, TEXT_COLOR) if i == 0 else font.render(line, True, TEXT_COLOR)
            screen.blit(surf, (panel_x, 12 + i * 22))

        pygame.display.flip()
        clock.tick(4)

    pygame.quit()
