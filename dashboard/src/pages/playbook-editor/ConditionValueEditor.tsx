interface ConditionValueEditorProps {
  conditionType: string;
  value: string;
  onChange: (val: string) => void;
}

export function ConditionValueEditor({ conditionType, value, onChange }: ConditionValueEditorProps) {
  let parsed: Record<string, any> = {};
  try { parsed = JSON.parse(value); } catch { parsed = {}; }

  const updateField = (field: string, val: any) => {
    const updated = { ...parsed, [field]: val };
    onChange(JSON.stringify(updated));
  };

  switch (conditionType) {
    case 'counterparty_type':
      return (
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700">Counterparty Type</label>
          <select
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
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

    case 'deal_size':
      return (
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700">Deal Size Range</label>
          <div className="flex gap-2 items-center">
            <input
              type="number"
              placeholder="Min ($)"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              value={parsed.min || ''}
              onChange={e => updateField('min', Number(e.target.value) || 0)}
            />
            <span className="text-gray-500">to</span>
            <input
              type="number"
              placeholder="Max ($)"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              value={parsed.max || ''}
              onChange={e => updateField('max', Number(e.target.value) || 0)}
            />
          </div>
        </div>
      );

    case 'jurisdiction':
      return (
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700">Jurisdiction</label>
          <select
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
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
          <label className="block text-sm font-medium text-gray-700">Contract Side</label>
          <select
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            value={parsed.value || ''}
            onChange={e => updateField('value', e.target.value)}
          >
            <option value="">Select side...</option>
            <option value="buyer">Buyer / Client</option>
            <option value="seller">Seller / Vendor</option>
          </select>
        </div>
      );

    case 'custom':
    default:
      return (
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700">Custom Value (JSON)</label>
          <textarea
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm font-mono"
            rows={3}
            value={value}
            onChange={e => onChange(e.target.value)}
            placeholder='{"key": "value"}'
          />
        </div>
      );
  }
}
