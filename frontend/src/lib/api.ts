import type { Mode, PlanResponse, ScenarioSummary } from './types'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(`${res.status} ${res.statusText}: ${text}`)
  }
  return res.json() as Promise<T>
}

export function fetchScenarios(): Promise<{ scenarios: ScenarioSummary[] }> {
  return request('/api/scenarios')
}

export function planScenario(scenarioName: string, mode: Mode): Promise<PlanResponse> {
  return request('/api/plan', {
    method: 'POST',
    body: JSON.stringify({ scenario_name: scenarioName, mode }),
  })
}
