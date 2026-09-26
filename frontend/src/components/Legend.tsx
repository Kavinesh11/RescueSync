const ITEMS = [
  { label: 'Engineer', swatch: 'bg-engineer', shape: 'rounded-full' },
  { label: 'Medic', swatch: 'bg-medic', shape: 'rounded-full' },
  { label: 'Wall', swatch: 'bg-wall', shape: 'rounded-sm' },
  { label: 'Rubble (blocked)', swatch: 'bg-rubble', shape: 'rounded-sm' },
  { label: 'Rubble (cleared)', swatch: 'bg-rubble-cleared', shape: 'rounded-sm' },
  { label: 'Victim', swatch: 'bg-victim', shape: 'rounded-full' },
  { label: 'Collision', swatch: 'bg-destructive', shape: 'rounded-full' },
]

export function Legend() {
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-2 text-xs text-muted-foreground">
      {ITEMS.map((item) => (
        <div key={item.label} className="flex items-center gap-1.5">
          <span className={`h-3 w-3 ${item.shape} ${item.swatch}`} />
          {item.label}
        </div>
      ))}
    </div>
  )
}
