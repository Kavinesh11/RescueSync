import { useMemo } from 'react'

import { cn } from '@/lib/utils'
import type { AgentState, Cell, Collision } from '@/lib/types'

const CELL_SIZE = 34

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
    <div
      className="relative select-none rounded-lg border border-border bg-floor shadow-inner"
      style={{ width: width * CELL_SIZE, height: height * CELL_SIZE }}
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
                'absolute flex items-center justify-center border border-black/10 text-[10px] transition-colors duration-200',
                ch === '#' && 'bg-wall',
                ch === '.' && 'bg-floor',
                ch === 'V' && 'bg-floor',
                ch === 'R' && !isOpen && 'bg-rubble',
                ch === 'R' && isOpen && 'bg-rubble-cleared',
                isCollidedCell && 'ring-2 ring-destructive ring-inset',
              )}
              style={{ left: c * CELL_SIZE, top: r * CELL_SIZE, width: CELL_SIZE, height: CELL_SIZE }}
              title={ch === 'R' ? (isOpen ? 'Rubble (cleared)' : 'Rubble (blocked)') : undefined}
            >
              {ch === 'V' && <span className="text-sm text-victim">&#9679;</span>}
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
              'absolute flex items-center justify-center rounded-full text-[11px] font-bold text-white shadow-lg transition-all duration-300 ease-out',
              collided && 'animate-pulse ring-4 ring-destructive',
              agent.failed && 'opacity-40 grayscale',
            )}
            style={{
              left: c * CELL_SIZE + 3,
              top: r * CELL_SIZE + 3,
              width: CELL_SIZE - 6,
              height: CELL_SIZE - 6,
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
  )
}
