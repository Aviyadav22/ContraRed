interface DependencyParamsEditorProps {
  effect: string;
  value: string;
  onChange: (val: string) => void;
}

export function DependencyParamsEditor({ effect, value, onChange }: DependencyParamsEditorProps) {
  let parsed: Record<string, any> = {};
  try { parsed = JSON.parse(value); } catch { parsed = {}; }

  const updateField = (field: string, val: any) => {
    const updated = { ...parsed, [field]: val };
    onChange(JSON.stringify(updated));
  };

  // Suppress unused variable warning — effect reserved for future per-effect layouts
  void effect;

  return (
    <div className="space-y-3">
      <div>
        <label className="block text-sm font-medium text-gray-700">Override Risk Level</label>
        <select
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
          value={parsed.risk_level || ''}
          onChange={e => updateField('risk_level', e.target.value)}
        >
          <option value="">No change</option>
          <option value="red">Critical (Red)</option>
          <option value="yellow">Warning (Yellow)</option>
          <option value="green">Safe (Green)</option>
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700">Override Position Text</label>
        <textarea
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
          rows={2}
          value={parsed.position_text || ''}
          onChange={e => updateField('position_text', e.target.value)}
          placeholder="Override negotiation position..."
        />
      </div>
      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="dep-suppress"
          checked={parsed.suppress || false}
          onChange={e => updateField('suppress', e.target.checked)}
          className="rounded border-gray-300"
        />
        <label htmlFor="dep-suppress" className="text-sm text-gray-700">Suppress this rule when dependency triggers</label>
      </div>
    </div>
  );
}
