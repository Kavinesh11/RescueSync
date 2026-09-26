import { AlertTriangle, CheckCircle2, Clock, Cpu, HeartPulse, Timer } from 'lucide-react'
import type { ReactNode } from 'react'

import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import type { Metrics } from '@/lib/types'

interface StatProps {
  icon: ReactNode
  label: string
  value: ReactNode
  tone?: 'default' | 'success' | 'destructive'
}

function Stat({ icon, label, value, tone = 'default' }: StatProps) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-border/60 bg-secondary/40 p-3">
      <div
        className={cn(
          'flex h-8 w-8 shrink-0 items-center justify-center rounded-md',
          tone === 'success' && 'bg-success/15 text-success',
          tone === 'destructive' && 'bg-destructive/15 text-destructive',
          tone === 'default' && 'bg-primary/15 text-primary',
        )}
      >
        {icon}
      </div>
      <div className="min-w-0">
        <div className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</div>
        <div className="truncate text-sm font-semibold">{value}</div>
      </div>
    </div>
  )
}

export function MetricsPanel({ metrics }: { metrics: Metrics }) {
  const allRescued = metrics.victims_rescued === metrics.victims_total
  return (
    <Card>
      <CardContent className="grid grid-cols-2 gap-2 p-3">
        <Stat
          icon={<HeartPulse className="h-4 w-4" />}
          label="Rescued"
          value={`${metrics.victims_rescued} / ${metrics.victims_total}`}
          tone={allRescued ? 'success' : 'default'}
        />
        <Stat
          icon={<AlertTriangle className="h-4 w-4" />}
          label="Collisions"
          value={metrics.collisions}
          tone={metrics.collisions === 0 ? 'success' : 'destructive'}
        />
        <Stat icon={<Clock className="h-4 w-4" />} label="Makespan" value={metrics.makespan} />
        <Stat icon={<Timer className="h-4 w-4" />} label="Wait actions" value={metrics.wait_actions} />
        <Stat
          icon={<Cpu className="h-4 w-4" />}
          label="Planning time"
          value={`${metrics.planning_time_ms} ms`}
        />
        <Stat
          icon={<CheckCircle2 className="h-4 w-4" />}
          label="Nodes expanded"
          value={metrics.nodes_expanded.toLocaleString()}
        />
      </CardContent>
    </Card>
  )
}
