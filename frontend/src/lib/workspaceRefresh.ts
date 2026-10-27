/** Tell open workspace views (dashboard queue) to refetch after agent or API workflow actions. */
export const WORKSPACE_DASHBOARD_REFRESH = 'workspace-dashboard-refresh'

export function notifyWorkspaceDashboardRefresh(): void {
  window.dispatchEvent(new CustomEvent(WORKSPACE_DASHBOARD_REFRESH))
}
