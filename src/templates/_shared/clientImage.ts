// Gemeinsamer Bild-Resolver für alle Branchen-Templates.
// Kundenbilder liegen unter src/assets/clients/<slug>/<datei>.
// import.meta.glob registriert sie zur Build-Zeit, damit astro:assets sie
// optimieren kann (WebP/AVIF). Liegt der Ordner leer vor (z.B. Showcase mit
// Demo-Daten ohne Bilder), ist die Map einfach leer — kein Fehler.
import type { ImageMetadata } from 'astro';

const images = import.meta.glob<{ default: ImageMetadata }>(
  '/src/assets/clients/**/*.{png,jpg,jpeg,webp,avif,svg}',
  { eager: true },
);

/**
 * Liefert die ImageMetadata für ein Kundenbild oder null (→ Template-Fallback).
 * @param slug  Kunden-Slug (= Ordnername unter src/assets/clients/)
 * @param file  Dateiname aus der Client-Config, oder null/undefined
 */
export function clientImage(slug: string, file?: string | null): ImageMetadata | null {
  if (!file) return null;
  const key = `/src/assets/clients/${slug}/${file}`;
  const mod = images[key];
  return mod ? mod.default : null;
}
