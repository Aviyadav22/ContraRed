interface ConditionPreviewProps {
  condition: { condition_type: string; operator: string; condition_value: string };
}

export function ConditionPreview({ condition }: ConditionPreviewProps) {
  let parsed: Record<string, any> = {};
  try { parsed = JSON.parse(condition.condition_value); } catch { return null; }

  const typeLabel: Record<string, string> = {
    counterparty_type: 'Counterparty',
    deal_size: 'Deal size',
    jurisdiction: 'Jurisdiction',
    contract_side: 'Contract side',
    custom: 'Custom',
  };

  const type = typeLabel[condition.condition_type] || condition.condition_type;
  const op = condition.operator;
  const val = parsed.value || (parsed.min && parsed.max ? `$${parsed.min.toLocaleString()} - $${parsed.max.toLocaleString()}` : JSON.stringify(parsed));

  return (
    <p className="text-xs text-indigo-600 mt-1 italic">
      When {type} {op} {val}
    </p>
  );
}
