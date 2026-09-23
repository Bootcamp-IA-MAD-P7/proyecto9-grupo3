import { useLanguage } from '../i18n';

export function SiteFooter() {
  const { language } = useLanguage();
  const english = language === 'en';
  return <footer className="site-footer"><div><strong>Review Desk</strong><span> · {english ? 'Human-in-the-loop moderation' : 'Moderación human-in-the-loop'}</span></div><nav aria-label={english ? 'Legal information' : 'Información legal'}><a href="/legal#privacy">{english ? 'Privacy' : 'Privacidad'}</a><a href="/legal#terms">{english ? 'Terms' : 'Términos'}</a><a href="/legal#credits">{english ? 'Credits & licenses' : 'Créditos y licencias'}</a></nav><small>{english ? 'Copyright holder not identified in this repository.' : 'Titular de derechos no identificado en este repositorio.'}</small></footer>;
}
