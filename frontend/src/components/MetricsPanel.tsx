import { AlertTriangle, Clock, Cpu, GitBranch, HeartPulse, Timer } from 'lucide-react'
import type { ReactNode } from 'react'

import { Card } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import type { Metrics } from '@/lib/types'

interface ReadoutProps {
  icon: ReactNode
  label: string
  value: ReactNode
  tone?: 'default' | 'success' | 'destructive'
}

function Readout({ icon, label, value, tone = 'default' }: ReadoutProps) {
  return (
    <div className="flex flex-col gap-1 border-b border-r border-border/60 px-3 py-2.5 [&:nth-child(2n)]:border-r-0 [&:nth-last-child(-n+2)]:border-b-0">
      <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-muted-foreground">
        <span className="text-muted-foreground/60">{icon}</span>
        {label}
      </div>
      <div
        className={cn(
          'truncate font-mono text-base font-semibold tabular-nums',
          tone === 'success' && 'text-success',
          tone === 'destructive' && 'text-destructive',
        )}
      >
        {value}
      </div>
    </div>
  )
}

export function MetricsPanel({ metrics }: { metrics: Metrics }) {
  const allRescued = metrics.victims_rescued === metrics.victims_total
  return (
    <Card className="overflow-hidden">
      <div className="flex items-center justify-between border-b border-border/60 bg-secondary/30 px-3 py-1.5">
        <span className="text-[10px] uppercase tracking-widest text-muted-foreground">Telemetry</span>
        <span className="font-mono text-[10px] uppercase tracking-widest text-hud">{metrics.mode}</span>
      </div>
      <div className="grid grid-cols-2">
        <Readout
          icon={<HeartPulse className="h-3.5 w-3.5" />}
          label="Rescued"
          value={`${metrics.victims_rescued} / ${metrics.victims_total}`}
          tone={allRescued ? 'success' : 'default'}
        />
        <Readout
          icon={<AlertTriangle className="h-3.5 w-3.5" />}
          label="Collisions"
          value={metrics.collisions}
          tone={metrics.collisions === 0 ? 'success' : 'destructive'}
        />
        <Readout icon={<Clock className="h-3.5 w-3.5" />} label="Makespan" value={metrics.makespan} />
        <Readout icon={<Timer className="h-3.5 w-3.5" />} label="Wait actions" value={metrics.wait_actions} />
        <Readout
          icon={<Cpu className="h-3.5 w-3.5" />}
          label="Planning time"
          value={`${metrics.planning_time_ms} ms`}
        />
        <Readout
          icon={<GitBranch className="h-3.5 w-3.5" />}
          label="Nodes expanded"
          value={metrics.nodes_expanded.toLocaleString()}
        />
      </div>
    </Card>
  )
}
