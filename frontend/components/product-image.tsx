import Image from "next/image";

import { brandColor, slugify } from "@/lib/format";

interface ProductImageProps {
  name: string;
  brand: string;
  imageUrl: string | null;
  size?: number;
  className?: string;
}

/**
 * Product thumbnail. Falls back to a deterministic branded placeholder
 * (brand initial on a brand-colored gradient) when no image is available —
 * keeps the demo self-contained and consistent with the Groww/Kite aesthetic.
 */
export function ProductImage({ name, brand, imageUrl, size = 48, className }: ProductImageProps) {
  const color = brandColor(brand);
  if (imageUrl) {
    return (
      <div className={`relative shrink-0 overflow-hidden rounded-lg ${className ?? ""}`} style={{ width: size, height: size }}>
        <Image src={imageUrl} alt={name} fill className="object-cover" unoptimized />
      </div>
    );
  }
  return (
    <div
      className={`flex shrink-0 select-none items-center justify-center overflow-hidden rounded-lg text-white ${className ?? ""}`}
      style={{
        width: size,
        height: size,
        background: `linear-gradient(135deg, ${color}, ${color}cc)`,
      }}
    >
      <span className="font-bold uppercase" style={{ fontSize: size * 0.42 }}>
        {brand.slice(0, 1)}
      </span>
      <span className="sr-only">{slugify(name)}</span>
    </div>
  );
}
