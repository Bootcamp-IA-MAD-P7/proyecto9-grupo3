interface StatusMessageProps {
  title: string;
  children?: string;
  tone?: 'neutral' | 'error';
}

export function StatusMessage({ title, children, tone = 'neutral' }: StatusMessageProps) {
  return (
    <div className={`status-message status-message--${tone}`} role={tone === 'error' ? 'alert' : undefined}>
      <strong>{title}</strong>
      <p>{children ?? 'Comprueba la conexión e inténtalo de nuevo.'}</p>
    </div>
  );
}
