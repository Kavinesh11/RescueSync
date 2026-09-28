import { useMemo } from 'react'

import { cn } from '@/lib/utils'
import type { AgentState, Cell, Collision } from '@/lib/types'

const CELL_SIZE = 38
const RULER = 18

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
            className="absolute flex items-center justify-center font-mono text-[9px] text-hud/70"
            style={{ left: RULER + c * CELL_SIZE, top: 0, width: CELL_SIZE, height: RULER }}
          >
            {c}
          </div>
        ))}
        {/* Row ruler */}
        {Array.from({ length: height }, (_, r) => (
          <div
            key={`row-${r}`}
            className="absolute flex items-center justify-center font-mono text-[9px] text-hud/70"
            style={{ left: 0, top: RULER + r * CELL_SIZE, width: RULER, height: CELL_SIZE }}
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
                  )}
                  style={{ left: c * CELL_SIZE, top: r * CELL_SIZE, width: CELL_SIZE, height: CELL_SIZE }}
                  title={ch === 'R' ? (isOpen ? 'Rubble (cleared)' : 'Rubble (blocked)') : undefined}
                >
                  {ch === 'V' && (
                    <span className="relative flex h-2.5 w-2.5">
                      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-victim/60" />
                      <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-victim shadow-[0_0_6px_hsl(var(--victim))]" />
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
            return (
              <div
                key={agent.id}
                className={cn(
                  'absolute flex items-center justify-center rounded-full font-mono text-[10px] font-semibold text-white shadow-lg ring-2 ring-black/20 transition-all duration-300 ease-out',
                  collided && 'animate-pulse ring-4 ring-destructive',
                  agent.failed && 'opacity-40 grayscale ring-dashed',
                )}
                style={{
                  left: c * CELL_SIZE + 4,
                  top: r * CELL_SIZE + 4,
                  width: CELL_SIZE - 8,
                  height: CELL_SIZE - 8,
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
