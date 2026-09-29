import { useMemo } from 'react'

import { cn } from '@/lib/utils'
import type { AgentState, Cell, Collision } from '@/lib/types'

interface GridCanvasProps {
  grid: string[]
  agents: Record<string, AgentState>
  t: number
  openTime: Record<string, number | null>
  collisionsAtT: Collision[]
}

function posAt(schedule: Cell[], t: number): Cell {
  const idx = Math.min(t, schedule.length - 1)
  return schedule[Math.max(idx, 0)]
}

export function GridCanvas({ grid, agents, t, openTime, collisionsAtT }: GridCanvasProps) {
  const height = grid.length
  const width = grid[0]?.length ?? 0

  // Scale cells to the scenario's own footprint instead of a fixed size, so
  // small scenarios (most of them) fill the card instead of leaving dead
  // space, while large_map (15x15) stays close to its previous, already-
  // tuned density.
  const CELL_SIZE = Math.min(56, Math.max(30, Math.floor(480 / Math.max(width, height))))
  const RULER = Math.round(Math.min(24, Math.max(16, CELL_SIZE * 0.32)))
  const rulerFontSize = Math.round(Math.min(12, Math.max(8, CELL_SIZE * 0.22)))
  const agentFontSize = Math.round(Math.min(15, Math.max(9, CELL_SIZE * 0.22)))
  const victimSize = Math.round(Math.min(16, Math.max(8, CELL_SIZE * 0.2)))

  const collidedAgents = useMemo(() => {
    const s = new Set<string>()
    for (const c of collisionsAtT) {
      s.add(c.agents[0])
      s.add(c.agents[1])
    }
    return s
  }, [collisionsAtT])

  const collidedCells = useMemo(() => {
    const s = new Set<string>()
    for (const c of collisionsAtT) {
      if (c.cell) s.add(`${c.cell[0]},${c.cell[1]}`)
    }
    return s
  }, [collisionsAtT])

  return (
    <div className="hud-frame inline-block p-3">
      <div
        className="relative select-none"
        style={{ width: RULER + width * CELL_SIZE, height: RULER + height * CELL_SIZE }}
      >
        {/* Column ruler */}
        {Array.from({ length: width }, (_, c) => (
          <div
            key={`col-${c}`}
            className="absolute flex items-center justify-center font-mono text-hud/70"
            style={{ left: RULER + c * CELL_SIZE, top: 0, width: CELL_SIZE, height: RULER, fontSize: rulerFontSize }}
          >
            {c}
          </div>
        ))}
        {/* Row ruler */}
        {Array.from({ length: height }, (_, r) => (
          <div
            key={`row-${r}`}
            className="absolute flex items-center justify-center font-mono text-hud/70"
            style={{ left: 0, top: RULER + r * CELL_SIZE, width: RULER, height: CELL_SIZE, fontSize: rulerFontSize }}
          >
            {r}
          </div>
        ))}

        <div
          className="absolute overflow-hidden rounded-sm border border-hud-dim bg-floor shadow-[inset_0_1px_12px_rgba(0,0,0,0.35)]"
          style={{ left: RULER, top: RULER, width: width * CELL_SIZE, height: height * CELL_SIZE }}
        >
          {/* Static grid cells */}
          {grid.map((row, r) =>
            [...row].map((ch, c) => {
              const key = `${r},${c}`
              const rubbleOpenAt = openTime[key]
              const isOpen = ch === 'R' && rubbleOpenAt !== null && rubbleOpenAt !== undefined && t >= rubbleOpenAt
              const justOpened = isOpen && t === rubbleOpenAt
              const isCollidedCell = collidedCells.has(key)
              return (
                <div
                  key={key}
                  className={cn(
                    'absolute flex items-center justify-center border border-black/20 transition-colors duration-200',
                    ch === '#' && 'bg-wall',
                    ch === '.' && 'bg-floor',
                    ch === 'V' && 'bg-floor',
                    ch === 'R' && !isOpen && 'bg-rubble',
                    ch === 'R' && isOpen && 'bg-rubble-cleared',
                    isCollidedCell && 'z-10 ring-2 ring-destructive ring-inset',
                    justOpened && 'animate-[pop-glow_450ms_ease-out]',
                  )}
                  style={{ left: c * CELL_SIZE, top: r * CELL_SIZE, width: CELL_SIZE, height: CELL_SIZE }}
                  title={ch === 'R' ? (isOpen ? 'Rubble (cleared)' : 'Rubble (blocked)') : undefined}
                >
                  {ch === 'V' && (
                    <span className="relative flex" style={{ width: victimSize, height: victimSize }}>
                      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-victim/60" />
                      <span
                        className="relative inline-flex rounded-full bg-victim shadow-[0_0_6px_hsl(var(--victim))]"
                        style={{ width: victimSize, height: victimSize }}
                      />
                    </span>
                  )}
                </div>
              )
            }),
          )}

          {/* Agents */}
          {Object.values(agents).map((agent) => {
            if (!agent.schedule.length) return null
            const [r, c] = posAt(agent.schedule, t)
            const collided = collidedAgents.has(agent.id)
            const isEngineer = agent.role === 'engineer'
            const justFinished = !isEngineer && !agent.failed && agent.finish_time != null && t === agent.finish_time
            return (
              <div
                key={agent.id}
                className={cn(
                  'absolute z-20 flex items-center justify-center rounded-full font-mono font-semibold text-white shadow-lg ring-2 ring-black/20 transition-all duration-300 ease-out',
                  collided && 'animate-pulse ring-4 ring-destructive',
                  !collided && !justFinished && t === 0 && 'animate-[fade-scale-in_300ms_ease-out_backwards]',
                  !collided && justFinished && 'animate-[success-pulse_500ms_ease-out]',
                  agent.failed && 'opacity-40 grayscale ring-dashed',
                )}
                style={{
                  left: c * CELL_SIZE + 4,
                  top: r * CELL_SIZE + 4,
                  width: CELL_SIZE - 8,
                  height: CELL_SIZE - 8,
                  fontSize: agentFontSize,
                  backgroundColor: collided
                    ? 'hsl(var(--destructive))'
                    : isEngineer
                      ? 'hsl(var(--engineer))'
                      : 'hsl(var(--medic))',
                }}
                title={`${agent.id} (${agent.role})${agent.failed ? ' — failed' : ''}`}
              >
                {agent.id}
              </div>
            )
          })}
        </div>
      </div>
      <span className="hud-corner-tr" />
      <span className="hud-corner-bl" />
    </div>
  )
}
