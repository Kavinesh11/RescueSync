import { ChevronLeft, ChevronRight, Pause, Play, RotateCcw } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Slider } from '@/components/ui/slider'

interface PlaybackControlsProps {
  t: number
  maxT: number
  playing: boolean
  speed: number
  onTChange: (t: number) => void
  onPlayingChange: (playing: boolean) => void
  onSpeedChange: (speed: number) => void
  onRestart: () => void
}

export function PlaybackControls({
  t,
  maxT,
  playing,
  speed,
  onTChange,
  onPlayingChange,
  onSpeedChange,
  onRestart,
}: PlaybackControlsProps) {
  const noTimeline = maxT === 0

  function handlePlayClick() {
    // Replaying after the timeline finished should restart from the top,
    // not just flip `playing` true for one tick and immediately snap back.
    if (!playing && t >= maxT) {
      onTChange(0)
    }
    onPlayingChange(!playing)
  }

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-border/60 bg-secondary/30 p-3">
      <div className="flex items-center gap-2">
        <Button size="icon" variant="outline" onClick={onRestart} disabled={noTimeline} title="Restart">
          <RotateCcw />
        </Button>
        <Button
          size="icon"
          variant="outline"
          onClick={() => onTChange(Math.max(0, t - 1))}
          disabled={t === 0}
          title="Step back"
        >
          <ChevronLeft />
        </Button>
        <Button size="icon" onClick={handlePlayClick} disabled={noTimeline} title={playing ? 'Pause' : 'Play'}>
          {playing ? <Pause /> : <Play />}
        </Button>
        <Button
          size="icon"
          variant="outline"
          onClick={() => onTChange(Math.min(maxT, t + 1))}
          disabled={t === maxT}
          title="Step forward"
        >
          <ChevronRight />
        </Button>
        <div className="ml-2 rounded border border-border/60 bg-background/60 px-2 py-1 font-mono text-sm tabular-nums text-hud">
          t={String(t).padStart(2, '0')}
          <span className="text-muted-foreground">/{String(maxT).padStart(2, '0')}</span>
        </div>
        {noTimeline && (
          <span className="text-[10px] uppercase tracking-wider text-destructive">
            No movement possible — see Mission Log
          </span>
        )}
        <div className="ml-auto flex items-center gap-2 text-[10px] uppercase tracking-wider text-muted-foreground">
          Speed
          <Slider
            className="w-24"
            min={1}
            max={10}
            step={1}
            value={[speed]}
            onValueChange={([v]) => onSpeedChange(v)}
          />
        </div>
      </div>
      <Slider min={0} max={Math.max(maxT, 1)} step={1} value={[t]} onValueChange={([v]) => onTChange(v)} />
    </div>
  )
}
