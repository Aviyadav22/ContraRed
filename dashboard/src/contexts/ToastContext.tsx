import { useState, useCallback, useRef, type ReactNode } from 'react';
import { ToastContext, type Toast, type ToastVariant } from './toast';

function uuid() {
  return Math.random().toString(36).substring(2, 10) + Date.now().toString(36);
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const timersRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  const removeToast = useCallback((id: string) => {
    const timer = timersRef.current.get(id);
    if (timer) { clearTimeout(timer); timersRef.current.delete(id); }
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  const addToast = useCallback((message: string, variant: ToastVariant) => {
    const id = uuid();
    setToasts(prev => [...prev.slice(-2), { id, message, variant }]);
    const timer = setTimeout(() => removeToast(id), 5000);
    timersRef.current.set(id, timer);
  }, [removeToast]);

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
      {children}
    </ToastContext.Provider>
  );
}
