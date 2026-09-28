import { Wrench, HeartPulse } from 'lucide-react'

import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'
import type { AgentState } from '@/lib/types'

function statusFor(agent: AgentState, t: number): { label: string; tone: 'success' | 'destructive' | 'default' } {
  if (agent.failed) return { label: 'FAILED', tone: 'destructive' }
  if (agent.finish_time !== null && t >= agent.finish_time) return { label: 'DONE', tone: 'success' }
  return { label: 'EN ROUTE', tone: 'default' }
}

export function AgentList({ agents, t }: { agents: Record<string, AgentState>; t: number }) {
  const sorted = Object.values(agents).sort((a, b) => a.id.localeCompare(b.id))
  return (
    <ScrollArea className="h-56 rounded-lg border border-border/60 bg-secondary/20">
      <div className="flex flex-col divide-y divide-border/60">
        {sorted.map((agent) => {
          const status = statusFor(agent, t)
          return (
            <div key={agent.id} className="flex items-center justify-between gap-2 px-3 py-2 text-sm">
              <div className="flex items-center gap-2.5">
                <span
                  className={cn(
                    'flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-white ring-2 ring-black/20',
                    agent.role === 'engineer' ? 'bg-engineer' : 'bg-medic',
                  )}
                >
                  {agent.role === 'engineer' ? <Wrench className="h-3 w-3" /> : <HeartPulse className="h-3 w-3" />}
                </span>
                <span className="font-mono font-medium">{agent.id}</span>
              </div>
              <span
                className={cn(
                  'flex items-center gap-1.5 font-mono text-[10px] tracking-wider',
                  status.tone === 'success' && 'text-success',
                  status.tone === 'destructive' && 'text-destructive',
                  status.tone === 'default' && 'text-muted-foreground',
                )}
              >
                <span
                  className={cn(
                    'h-1.5 w-1.5 rounded-full',
                    status.tone === 'success' && 'bg-success',
                    status.tone === 'destructive' && 'bg-destructive',
                    status.tone === 'default' && 'animate-pulse bg-primary',
                  )}
                />
                {status.label}
              </span>
            </div>
          )
        })}
      </div>
    </ScrollArea>
  )
}
