const TOOL_LABELS: Record<string, string> = {
  run_return_investigation: 'Ran return investigation',
  get_return_details: 'Looked up return details',
  get_order_details: 'Looked up order details',
  get_order_item: 'Looked up order line item',
  get_product_details: 'Looked up product details',
  get_product_unit: 'Looked up serial unit',
  get_delivery_details: 'Checked delivery details',
  get_return_shipment: 'Checked return shipment',
  calculate_refundable_amount: 'Calculated refundable amount',
  get_delivery_status: 'Checked delivery status',
  get_inspection_results: 'Checked inspection results',
  get_refund_status: 'Checked refund ledger',
  get_customer_return_history: 'Reviewed customer history',
  search_return_policy: 'Searched return policy',
  search_inspection_reports: 'Searched inspection reports',
  search_customer_complaints: 'Searched customer complaints',
  search_warranty_documents: 'Searched warranty documents',
  search_supplier_reports: 'Searched supplier reports',
  search_support_communications: 'Searched support emails',
  search_refurbishment_guidelines: 'Searched refurbishment guidelines',
  resolve_applicable_policy: 'Resolved applicable policy',
  build_return_timeline_tool: 'Built return timeline',
  detect_return_inconsistencies_tool: 'Checked evidence inconsistencies',
  analyze_product_complaint_patterns_tool: 'Analyzed complaint patterns',
  get_recovery_options: 'Compared recovery options',
  get_recovery_recommendation: 'Scored recovery recommendation',
  submit_create_investigation_case: 'Submitted investigation case',
  submit_refund_request: 'Submitted refund request',
  submit_repair_recovery_task: 'Submitted repair task',
  submit_refurbishment_task: 'Submitted refurbishment task',
  submit_inspection_task: 'Requested inspection task',
  submit_supplier_return_task: 'Submitted supplier return task',
  submit_recycle_task: 'Submitted recycling task',
  submit_evidence_request: 'Requested additional evidence',
  execute_action_request: 'Executed approved action',
  get_action_request_status: 'Checked request status',
  list_returns: 'Listed returns',
  list_refunds_awaiting_approval: 'Listed refunds awaiting approval',
  list_open_investigation_cases: 'Listed open cases',
  list_actions_for_return: 'Listed actions for return',
  get_monitoring_overview: 'Checked monitoring overview',
  approve_action_request: 'Approved action',
  assign_investigation_case: 'Assigned case',
}

export function friendlyToolLabel(toolName: string | null | undefined): string {
  if (!toolName) return 'Working'
  if (TOOL_LABELS[toolName]) return TOOL_LABELS[toolName]
  return toolName
    .replace(/^get_|^search_|^submit_|^list_/g, '')
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ')
}

export function friendlyToolProgress(toolName: string | null | undefined): string {
  const base = friendlyToolLabel(toolName)
  if (base.endsWith('…')) return base
  if (base.startsWith('Ran') || base.startsWith('Looked') || base.startsWith('Checked')) {
    return `${base}…`
  }
  return `${base}…`
}
