import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import type { ScenarioSummary } from '@/lib/types'

interface ScenarioSelectProps {
  scenarios: ScenarioSummary[]
  value: string
  onChange: (name: string) => void
}

export function ScenarioSelect({ scenarios, value, onChange }: ScenarioSelectProps) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger className="w-56">
        <SelectValue placeholder="Choose a scenario" />
      </SelectTrigger>
      <SelectContent>
        {scenarios.map((s) => (
          <SelectItem key={s.name} value={s.name}>
            {s.name.replaceAll('_', ' ')}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
