/** Indian-rupee formatting & misc helpers (lakh/crore grouping). */

/** Format an amount with Indian digit grouping: 145999 → ₹1,45,999 */
export function formatINR(amount: number | null | undefined): string {
  const value = Math.round(Number(amount ?? 0));
  if (Number.isNaN(value)) return "₹0";
  if (value < 0) return "-" + formatINR(-value);
  if (value < 1000) return `₹${value}`;
  const s = String(value);
  const last3 = s.slice(-3);
  const rest = s.slice(0, -3);
  const grouped = rest.replace(/\B(?=(\d{2})+(?!\d))/g, ",");
  return `₹${grouped ? grouped + "," : ""}${last3}`;
}

/** Compact Indian formatting for large counts: 23456 → 23.4k (or 1.2L for lakhs). */
export function formatCompact(value: number): string {
  if (value >= 100000) return `${(value / 100000).toFixed(1)}L`;
  if (value >= 1000) return `${(value / 1000).toFixed(1)}k`;
  return String(value);
}

export function formatPercent(value: number, sign = true): string {
  const v = Number.isFinite(value) ? value : 0;
  return `${sign && v > 0 ? "+" : ""}${v.toFixed(1)}%`;
}

/** Relative time: "2 min ago", "3 h ago". */
export function timeAgo(iso: string | null | undefined): string {
  if (!iso) return "—";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "—";
  const diff = Math.max(0, Date.now() - then);
  const sec = Math.floor(diff / 1000);
  if (sec < 60) return "just now";
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min} min ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr} hr ago`;
  const days = Math.floor(hr / 24);
  return `${days} day${days > 1 ? "s" : ""} ago`;
}

/** Local time for a sync timestamp. */
export function formatTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short" });
}

/** Star rating → small label like "4.5" */
export function formatRating(rating: number): string {
  return (Number.isFinite(rating) ? rating : 0).toFixed(1);
}

/** Build a slug used for deterministic placeholder images. */
export function slugify(name: string): string {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "").slice(0, 40);
}

/** Brand → deterministic accent color for the image placeholder. */
const BRAND_COLORS: Record<string, string> = {
  Samsung: "#1428A0",
  Xiaomi: "#FF6900",
  OnePlus: "#EB0028",
  Realme: "#FFD800",
  iQOO: "#150F2D",
  HP: "#0096D6",
  Dell: "#007DB8",
  Lenovo: "#E2231A",
  ASUS: "#00539B",
  LG: "#A50034",
  Bosch: "#BA0C2F",
  Voltas: "#007B3D",
};

export function brandColor(brand: string): string {
  return BRAND_COLORS[brand] ?? "#6B7280";
}
