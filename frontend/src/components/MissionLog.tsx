import { useMemo } from 'react'

import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'
import type { AgentState, Collision } from '@/lib/types'

interface LogEvent {
  t: number
  text: string
  tone: 'default' | 'success' | 'destructive'
}

function buildLog(
  agents: Record<string, AgentState>,
  openTime: Record<string, number | null>,
  collisions: Collision[],
): LogEvent[] {
  const events: LogEvent[] = []
  const sorted = Object.values(agents).sort((a, b) => a.id.localeCompare(b.id))

  for (const agent of sorted) {
    const [sr, sc] = agent.schedule[0] ?? [0, 0]
    events.push({ t: 0, text: `${agent.id} deployed at (${sr}, ${sc})`, tone: 'default' })

    if (agent.role === 'engineer' && agent.rubble) {
      const rubbleKey = `${agent.rubble[0]},${agent.rubble[1]}`
      const openAt = openTime[rubbleKey]
      if (agent.clear_start_time != null) {
        events.push({
          t: agent.clear_start_time,
          text: `${agent.id} reaches rubble at (${agent.rubble[0]}, ${agent.rubble[1]}) — begins clearing`,
          tone: 'default',
        })
      }
      if (openAt != null) {
        events.push({
          t: openAt,
          text: `Rubble at (${agent.rubble[0]}, ${agent.rubble[1]}) cleared — route open`,
          tone: 'success',
        })
      }
      if (agent.finish_time != null && !agent.failed && agent.park) {
        events.push({ t: agent.finish_time, text: `${agent.id} parks at (${agent.park[0]}, ${agent.park[1]})`, tone: 'default' })
      }
    } else if (agent.role === 'medic' && agent.victim) {
      if (agent.rescue_start_time != null) {
        events.push({
          t: agent.rescue_start_time,
          text: `${agent.id} reaches victim at (${agent.victim[0]}, ${agent.victim[1]}) — begins rescue`,
          tone: 'default',
        })
      }
      if (agent.finish_time != null && !agent.failed) {
        events.push({ t: agent.finish_time, text: `${agent.id} rescue complete`, tone: 'success' })
      }
    }

    if (agent.failed) {
      const stuckAt = Math.max(0, agent.schedule.length - 1)
      events.push({ t: stuckAt, text: `${agent.id} failed to complete its mission`, tone: 'destructive' })
    }
  }

  for (const c of collisions) {
    events.push({ t: c.t, text: `Collision (${c.kind}) — ${c.agents.join(' × ')}`, tone: 'destructive' })
  }

  return events.sort((a, b) => a.t - b.t)
}

export function MissionLog({
  agents,
  openTime,
  collisions,
  t,
}: {
  agents: Record<string, AgentState>
  openTime: Record<string, number | null>
  collisions: Collision[]
  t: number
}) {
  const events = useMemo(() => buildLog(agents, openTime, collisions), [agents, openTime, collisions])

  return (
    <ScrollArea className="h-36 rounded-lg border border-border/60 bg-secondary/20">
      <div className="flex flex-col divide-y divide-border/40">
        {events.map((e, i) => {
          const occurred = e.t <= t
          return (
            <div
              key={i}
              className={cn('flex items-start gap-2 px-3 py-1.5 text-xs transition-opacity', !occurred && 'opacity-30')}
            >
              <span className="mt-px shrink-0 font-mono text-[10px] text-hud">t={String(e.t).padStart(2, '0')}</span>
              <span className={cn(e.tone === 'success' && 'text-success', e.tone === 'destructive' && 'text-destructive')}>
                {e.text}
              </span>
            </div>
          )
        })}
      </div>
    </ScrollArea>
  )
}
