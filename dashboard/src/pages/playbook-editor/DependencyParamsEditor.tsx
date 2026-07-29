interface DependencyParamsEditorProps {
  effect: string;
  value: string;
  onChange: (val: string) => void;
}

export function DependencyParamsEditor({ effect, value, onChange }: DependencyParamsEditorProps) {
  let parsed: { new_risk?: string; new_position?: string; message?: string } = {};
  try { parsed = JSON.parse(value); } catch { parsed = {}; }

  const updateField = (field: string, val: string) => {
    onChange(JSON.stringify({ ...parsed, [field]: val }));
  };

  if (effect === 'escalate_risk') {
    return (
      <div>
        <label className="block text-sm font-medium text-[var(--text-primary)]">New Risk Level</label>
        <select
          className="w-full rounded-lg border border-[var(--border)] px-3 py-2 text-sm"
          value={parsed.new_risk || ''}
          onChange={e => updateField('new_risk', e.target.value)}
        >
          <option value="">Select risk...</option>
          <option value="RED">Critical (Red)</option>
          <option value="YELLOW">Warning (Yellow)</option>
          <option value="GREEN">Safe (Green)</option>
        </select>
      </div>
    );
  }

  if (effect === 'add_flag') {
    return (
      <div>
        <label className="block text-sm font-medium text-[var(--text-primary)]">Flag Message</label>
        <input
          className="w-full rounded-lg border border-[var(--border)] px-3 py-2 text-sm"
          value={parsed.message || ''}
          onChange={e => updateField('message', e.target.value)}
          placeholder="Explain the cross-clause issue to the reviewer."
        />
      </div>
    );
  }

  if (effect === 'change_position') {
    return (
      <div>
        <label className="block text-sm font-medium text-[var(--text-primary)]">New Position Text</label>
        <textarea
          className="w-full rounded-lg border border-[var(--border)] px-3 py-2 text-sm"
          rows={2}
          value={parsed.new_position || ''}
          onChange={e => updateField('new_position', e.target.value)}
          placeholder="Override negotiation position..."
        />
      </div>
    );
  }

  return (
    <p className="text-sm text-[var(--text-muted)]">
      No parameters are required. The target rule will be suppressed when the trigger matches.
    </p>
  );
}
