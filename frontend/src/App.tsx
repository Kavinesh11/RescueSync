import { AlertCircle, Loader2, Radar } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'

import { AgentList } from '@/components/AgentList'
import { GridCanvas } from '@/components/GridCanvas'
import { Legend } from '@/components/Legend'
import { MetricsPanel } from '@/components/MetricsPanel'
import { MissionLog } from '@/components/MissionLog'
import { ModeSwitch } from '@/components/ModeSwitch'
import { PlaybackControls } from '@/components/PlaybackControls'
import { ScenarioSelect } from '@/components/ScenarioSelect'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { fetchScenarios, planScenario } from '@/lib/api'
import type { Mode, PlanResponse, ScenarioSummary } from '@/lib/types'

export default function App() {
  const [scenarios, setScenarios] = useState<ScenarioSummary[]>([])
  const [scenarioName, setScenarioName] = useState<string>('')
  const [mode, setMode] = useState<Mode>('rescuesync')
  const [plan, setPlan] = useState<PlanResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [t, setT] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(4)

  useEffect(() => {
    fetchScenarios()
      .then((res) => {
        setScenarios(res.scenarios)
        if (res.scenarios.length > 0) setScenarioName(res.scenarios[0].name)
      })
      .catch((e) => setError(String(e)))
  }, [])

  useEffect(() => {
    if (!scenarioName) return
    setLoading(true)
    setError(null)
    planScenario(scenarioName, mode)
      .then((res) => {
        setPlan(res)
        setT(0)
        setPlaying(false)
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false))
  }, [scenarioName, mode])

  const maxT = useMemo(() => {
    if (!plan) return 0
    return Math.max(0, ...Object.values(plan.agents).map((a) => a.schedule.length - 1))
  }, [plan])

  useEffect(() => {
    if (!playing) return
    const interval = setInterval(() => {
      setT((prev) => {
        if (prev >= maxT) {
          setPlaying(false)
          return prev
        }
        return prev + 1
      })
    }, 700 / speed)
    return () => clearInterval(interval)
  }, [playing, speed, maxT])

  const restart = useCallback(() => {
    setT(0)
    setPlaying(false)
  }, [])

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.target instanceof HTMLElement && ['INPUT', 'TEXTAREA'].includes(e.target.tagName)) return
      if (e.code === 'Space') {
        e.preventDefault()
        setPlaying((p) => !p)
      } else if (e.code === 'ArrowRight') {
        setT((p) => Math.min(maxT, p + 1))
      } else if (e.code === 'ArrowLeft') {
        setT((p) => Math.max(0, p - 1))
      } else if (e.key === 'r' || e.key === 'R') {
        restart()
      } else if (e.key === '1') {
        setMode('independent')
      } else if (e.key === '2') {
        setMode('cooperative')
      } else if (e.key === '3') {
        setMode('rescuesync')
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [maxT, restart])

  const collisionsAtT = useMemo(() => {
    if (!plan) return []
    return plan.metrics.collision_details.filter((c) => c.t === t)
  }, [plan, t])

  const currentScenario = scenarios.find((s) => s.name === scenarioName)

  return (
    <div className="min-h-screen bg-[radial-gradient(ellipse_at_top,hsl(var(--primary)/0.07),transparent_55%)] bg-background pb-16">
      <header className="border-b border-hud-dim bg-card/60 backdrop-blur-sm">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-4 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="hud-frame flex h-10 w-10 shrink-0 items-center justify-center bg-primary/10 text-primary">
              <Radar className="h-5 w-5 animate-[spin_6s_linear_infinite]" />
              <span className="hud-corner-tr" />
              <span className="hud-corner-bl" />
            </div>
            <div>
              <h1 className="text-lg font-semibold leading-tight tracking-tight">RescueSync</h1>
              <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                Cooperative Multi-Agent Rescue Planner
              </p>
            </div>
          </div>
          <div className="ml-auto flex flex-wrap items-center gap-3">
            <ScenarioSelect scenarios={scenarios} value={scenarioName} onChange={setScenarioName} />
            <ModeSwitch mode={mode} onChange={setMode} />
          </div>
        </div>
      </header>

      <main className="mx-auto grid max-w-7xl grid-cols-1 gap-6 px-6 py-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="flex flex-col gap-4">
          <Card>
            <CardHeader className="flex-row items-center justify-between gap-2">
              <div>
                <div className="font-mono text-[10px] uppercase tracking-widest text-hud">Scenario</div>
                <CardTitle className="mt-0.5">{scenarioName ? scenarioName.replaceAll('_', ' ') : 'Loading…'}</CardTitle>
                <CardDescription>{currentScenario?.description}</CardDescription>
              </div>
              {loading && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              {error && (
                <div className="flex items-center gap-2 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                  <AlertCircle className="h-4 w-4 shrink-0" />
                  {error}
                </div>
              )}
              {plan && (
                <div key={`${scenarioName}-${mode}`} className="flex flex-col gap-4 animate-[content-fade-in_250ms_ease-out]">
                  <div className="overflow-auto rounded-md border border-border/40 bg-[radial-gradient(circle_at_center,hsl(var(--secondary)/0.4),transparent_70%)] p-4">
                    <GridCanvas
                      grid={plan.grid}
                      agents={plan.agents}
                      t={t}
                      openTime={plan.open_time}
                      collisionsAtT={collisionsAtT}
                    />
                  </div>
                  <PlaybackControls
                    t={t}
                    maxT={maxT}
                    playing={playing}
                    speed={speed}
                    onTChange={setT}
                    onPlayingChange={setPlaying}
                    onSpeedChange={setSpeed}
                    onRestart={restart}
                  />
                  <Separator />
                  <Legend />
                  <Separator />
                  <div>
                    <div className="mb-2 font-mono text-[10px] uppercase tracking-widest text-hud">Mission Log</div>
                    <MissionLog
                      agents={plan.agents}
                      openTime={plan.open_time}
                      collisions={plan.metrics.collision_details}
                      t={t}
                    />
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="flex flex-col gap-4">
          {plan && <MetricsPanel metrics={plan.metrics} />}
          <Card>
            <CardHeader>
              <CardTitle>Agents</CardTitle>
            </CardHeader>
            <CardContent>{plan && <AgentList agents={plan.agents} t={t} />}</CardContent>
          </Card>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 px-1 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
            <span className="flex items-center gap-1"><kbd className="rounded border border-border/60 px-1">Space</kbd> play/pause</span>
            <span className="flex items-center gap-1"><kbd className="rounded border border-border/60 px-1">←/→</kbd> step</span>
            <span className="flex items-center gap-1"><kbd className="rounded border border-border/60 px-1">1/2/3</kbd> mode</span>
            <span className="flex items-center gap-1"><kbd className="rounded border border-border/60 px-1">R</kbd> restart</span>
          </div>
        </div>
      </main>
    </div>
  )
}
