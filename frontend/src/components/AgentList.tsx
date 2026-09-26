import { Wrench, HeartPulse } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'
import type { AgentState } from '@/lib/types'

function statusFor(agent: AgentState, t: number): { label: string; tone: 'success' | 'destructive' | 'secondary' | 'default' } {
  if (agent.failed) return { label: 'Failed', tone: 'destructive' }
  if (agent.finish_time !== null && t >= agent.finish_time) return { label: 'Done', tone: 'success' }
  return { label: 'En route', tone: 'default' }
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
              <div className="flex items-center gap-2">
                <span
                  className={cn(
                    'flex h-6 w-6 items-center justify-center rounded-full text-white',
                    agent.role === 'engineer' ? 'bg-engineer' : 'bg-medic',
                  )}
                >
                  {agent.role === 'engineer' ? <Wrench className="h-3 w-3" /> : <HeartPulse className="h-3 w-3" />}
                </span>
                <span className="font-medium">{agent.id}</span>
              </div>
              <Badge variant={status.tone === 'default' ? 'outline' : status.tone}>{status.label}</Badge>
            </div>
          )
        })}
      </div>
    </ScrollArea>
  )
}
