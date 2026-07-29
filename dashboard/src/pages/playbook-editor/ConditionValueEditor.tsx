interface ConditionValueEditorProps {
  conditionType: string;
  operator: string;
  value: string;
  onChange: (val: string) => void;
}

export function ConditionValueEditor({ conditionType, operator, value, onChange }: ConditionValueEditorProps) {
  let parsed: {
    value?: string;
    values?: string[];
    threshold?: number;
    min?: number;
    max?: number;
  } = {};
  try { parsed = JSON.parse(value); } catch { parsed = {}; }

  const updateField = (field: string, val: string | number) => {
    const updated = { ...parsed, [field]: val };
    onChange(JSON.stringify(updated));
  };

  if (conditionType === 'deal_size') {
    if (operator === 'between') {
      return (
        <div className="space-y-2">
          <label className="block text-sm font-medium text-[var(--text-primary)]">Deal Size Range</label>
          <div className="flex gap-2 items-center">
            <input
              type="number"
              min={0}
              placeholder="Min ($)"
              className="w-full rounded-lg border border-[var(--border)] px-3 py-2 text-sm"
              value={parsed.min ?? ''}
              onChange={e => updateField('min', Number(e.target.value))}
            />
            <span className="text-[var(--text-muted)]">to</span>
            <input
              type="number"
              min={0}
              placeholder="Max ($)"
              className="w-full rounded-lg border border-[var(--border)] px-3 py-2 text-sm"
              value={parsed.max ?? ''}
              onChange={e => updateField('max', Number(e.target.value))}
            />
          </div>
        </div>
      );
    }
    return (
      <div className="space-y-2">
        <label className="block text-sm font-medium text-[var(--text-primary)]">Deal Size Threshold</label>
        <input
          type="number"
          min={0}
          placeholder="Amount ($)"
          className="w-full rounded-lg border border-[var(--border)] px-3 py-2 text-sm"
          value={parsed.threshold ?? ''}
          onChange={e => updateField('threshold', Number(e.target.value))}
        />
      </div>
    );
  }

  if (operator === 'in' || operator === 'not_in') {
    return (
      <div className="space-y-2">
        <label className="block text-sm font-medium text-[var(--text-primary)]">
          Values (one per line)
        </label>
        <textarea
          className="w-full rounded-lg border border-[var(--border)] px-3 py-2 text-sm"
          rows={3}
          value={(parsed.values || []).join('\n')}
          onChange={e => onChange(JSON.stringify({
            values: e.target.value.split('\n').map(item => item.trim()).filter(Boolean),
          }))}
        />
      </div>
    );
  }

  switch (conditionType) {
    case 'counterparty_type':
      return (
        <div className="space-y-2">
          <label className="block text-sm font-medium text-[var(--text-primary)]">Counterparty Type</label>
          <select
            className="w-full rounded-lg border border-[var(--border)] px-3 py-2 text-sm"
            value={parsed.value || ''}
            onChange={e => updateField('value', e.target.value)}
          >
            <option value="">Select type...</option>
            <option value="enterprise">Enterprise</option>
            <option value="fortune_500">Fortune 500</option>
            <option value="startup">Startup</option>
            <option value="government">Government</option>
            <option value="non_profit">Non-Profit</option>
            <option value="individual">Individual</option>
          </select>
        </div>
      );

    case 'jurisdiction':
      return (
        <div className="space-y-2">
          <label className="block text-sm font-medium text-[var(--text-primary)]">Jurisdiction</label>
          <select
            className="w-full rounded-lg border border-[var(--border)] px-3 py-2 text-sm"
            value={parsed.value || ''}
            onChange={e => updateField('value', e.target.value)}
          >
            <option value="">Select jurisdiction...</option>
            <option value="IN">India</option>
            <option value="DE-US">Delaware, USA</option>
            <option value="NY-US">New York, USA</option>
            <option value="CA-US">California, USA</option>
            <option value="GB-EW">England & Wales</option>
            <option value="SG">Singapore</option>
            <option value="AE-DIFC">UAE - DIFC</option>
            <option value="AE">UAE - Onshore</option>
            <option value="DE">Germany</option>
            <option value="FR">France</option>
            <option value="HK">Hong Kong</option>
            <option value="AU">Australia</option>
            <option value="JP">Japan</option>
          </select>
        </div>
      );

    case 'contract_side':
      return (
        <div className="space-y-2">
          <label className="block text-sm font-medium text-[var(--text-primary)]">Contract Side</label>
          <select
            className="w-full rounded-lg border border-[var(--border)] px-3 py-2 text-sm"
            value={parsed.value || ''}
            onChange={e => updateField('value', e.target.value)}
          >
            <option value="">Select side...</option>
            <option value="customer">Customer / Client</option>
            <option value="vendor">Vendor / Seller</option>
          </select>
        </div>
      );

    case 'custom':
    default:
      return (
        <div className="space-y-2">
          <label className="block text-sm font-medium text-[var(--text-primary)]">Custom Value (JSON)</label>
          <textarea
            className="w-full rounded-lg border border-[var(--border)] px-3 py-2 text-sm font-mono"
            rows={3}
            value={value}
            onChange={e => onChange(e.target.value)}
            placeholder='{"key": "value"}'
          />
        </div>
      );
  }
}
