import { Link } from 'react-router-dom'
import { agentNav } from '../../lib/workflowAgent'
import { button } from '../ui/styles'

export function AskAgentLink({
  returnId,
  draftMessage,
  variant = 'primary',
  className,
}: {
  returnId: string
  draftMessage: string
  variant?: 'primary' | 'secondary' | 'ghost'
  className?: string
}) {
  const nav = agentNav(returnId, draftMessage)
  return (
    <Link to={nav.to} state={nav.state} className={className ?? button(variant, 'sm')}>
      Ask agent
    </Link>
  )
}
