import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import type { Mode } from '@/lib/types'

const MODES: { value: Mode; label: string }[] = [
  { value: 'independent', label: 'Independent A*' },
  { value: 'cooperative', label: 'Cooperative A*' },
  { value: 'rescuesync', label: 'RescueSync' },
]

export function ModeSwitch({ mode, onChange }: { mode: Mode; onChange: (m: Mode) => void }) {
  return (
    <Tabs value={mode} onValueChange={(v) => onChange(v as Mode)}>
      <TabsList>
        {MODES.map((m) => (
          <TabsTrigger key={m.value} value={m.value}>
            {m.label}
          </TabsTrigger>
        ))}
      </TabsList>
    </Tabs>
  )
}
