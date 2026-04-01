import { forwardRef, type InputHTMLAttributes, type SelectHTMLAttributes, type TextareaHTMLAttributes, type ReactNode, type CSSProperties } from 'react';

/* -------------------------------------------------------------------------- */
/*  InputWrapper                                                               */
/* -------------------------------------------------------------------------- */

interface WrapperProps {
  label?: string;
  error?: string;
  helperText?: string;
  children: ReactNode;
}

function InputWrapper({ label, error, helperText, children }: WrapperProps) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      {label && (
        <label style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-secondary)' }}>
          {label}
        </label>
      )}
      {children}
      {error && (
        <span style={{ fontSize: 12, color: 'var(--risk-critical)' }}>{error}</span>
      )}
      {helperText && !error && (
        <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{helperText}</span>
      )}
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/*  Shared base style                                                          */
/* -------------------------------------------------------------------------- */

const baseInputStyle: CSSProperties = {
  height: 40,
  fontSize: 14,
  fontFamily: 'var(--font-sans)',
  backgroundColor: 'var(--bg-surface)',
  color: 'var(--text-primary)',
  border: '1px solid var(--border)',
  borderRadius: 'var(--radius-sm)',
  padding: '0 12px',
  outline: 'none',
  transition: 'border-color var(--transition-fast), box-shadow var(--transition-fast)',
  width: '100%',
};

function focusHandler(e: React.FocusEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) {
  e.currentTarget.style.borderColor = 'var(--accent)';
  e.currentTarget.style.boxShadow = '0 0 0 3px var(--accent-glow)';
}

function blurHandler(e: React.FocusEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>, hasError: boolean) {
  e.currentTarget.style.borderColor = hasError ? 'var(--risk-critical)' : 'var(--border)';
  e.currentTarget.style.boxShadow = hasError ? '0 0 0 3px var(--risk-critical-bg)' : '';
}

function errorStyle(error?: string): CSSProperties {
  if (!error) return {};
  return { borderColor: 'var(--risk-critical)', boxShadow: '0 0 0 3px var(--risk-critical-bg)' };
}

/* -------------------------------------------------------------------------- */
/*  TextInput                                                                  */
/* -------------------------------------------------------------------------- */

interface TextInputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

export const TextInput = forwardRef<HTMLInputElement, TextInputProps>(
  ({ label, error, helperText, style, ...rest }, ref) => (
    <InputWrapper label={label} error={error} helperText={helperText}>
      <input
        ref={ref}
        style={{ ...baseInputStyle, ...errorStyle(error), ...style }}
        onFocus={focusHandler}
        onBlur={(e) => blurHandler(e, !!error)}
        {...rest}
      />
    </InputWrapper>
  )
);
TextInput.displayName = 'TextInput';

/* -------------------------------------------------------------------------- */
/*  SelectInput                                                                */
/* -------------------------------------------------------------------------- */

interface SelectInputProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  helperText?: string;
  children: ReactNode;
}

const chevronSvg = `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2394A3B8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E")`;

export const SelectInput = forwardRef<HTMLSelectElement, SelectInputProps>(
  ({ label, error, helperText, style, children, ...rest }, ref) => (
    <InputWrapper label={label} error={error} helperText={helperText}>
      <select
        ref={ref}
        style={{
          ...baseInputStyle,
          paddingRight: 32,
          appearance: 'none' as const,
          backgroundImage: chevronSvg,
          backgroundRepeat: 'no-repeat',
          backgroundPosition: 'right 10px center',
          cursor: 'pointer',
          ...errorStyle(error),
          ...style,
        }}
        onFocus={focusHandler as any}
        onBlur={(e) => blurHandler(e as any, !!error)}
        {...rest}
      >
        {children}
      </select>
    </InputWrapper>
  )
);
SelectInput.displayName = 'SelectInput';

/* -------------------------------------------------------------------------- */
/*  TextareaInput                                                              */
/* -------------------------------------------------------------------------- */

interface TextareaInputProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

export const TextareaInput = forwardRef<HTMLTextAreaElement, TextareaInputProps>(
  ({ label, error, helperText, style, ...rest }, ref) => (
    <InputWrapper label={label} error={error} helperText={helperText}>
      <textarea
        ref={ref}
        style={{
          ...baseInputStyle,
          height: 'auto',
          minHeight: 80,
          resize: 'vertical',
          padding: '10px 12px',
          ...errorStyle(error),
          ...style,
        }}
        onFocus={focusHandler as any}
        onBlur={(e) => blurHandler(e as any, !!error)}
        {...rest}
      />
    </InputWrapper>
  )
);
TextareaInput.displayName = 'TextareaInput';
