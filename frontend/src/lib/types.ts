export type Mode = 'independent' | 'cooperative' | 'rescuesync'

export type Cell = [number, number]

export interface ScenarioSummary {
  name: string
  description: string
  width: number
  height: number
  num_agents: number
}

export interface AgentState {
  id: string
  role: 'engineer' | 'medic'
  schedule: Cell[]
  failed: boolean
  finish_time: number | null
  rubble?: Cell
  stand?: Cell
  park?: Cell
  clear_start_time?: number | null
  victim?: Cell
  rescue_start_time?: number | null
}

export interface Collision {
  kind: 'vertex' | 'swap'
  t: number
  cell: Cell | null
  agents: [string, string]
}

export interface Metrics {
  mode: Mode
  victims_rescued: number
  victims_total: number
  success_rate: number
  collisions: number
  collision_details: Collision[]
  makespan: number
  sum_of_costs: number
  wait_actions: number
  medic_dependency_wait: number
  planning_time_ms: number
  nodes_expanded: number
  agents_failed: string[]
}

export interface PlanResponse {
  mode: Mode
  grid: string[]
  max_time: number
  agents: Record<string, AgentState>
  open_time: Record<string, number | null>
  metrics: Metrics
}
