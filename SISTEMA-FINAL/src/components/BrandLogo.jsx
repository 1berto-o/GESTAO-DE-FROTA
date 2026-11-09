const VARIANTS = {
  horizontal: '/brand/logo-horizontal.svg',
  vertical: '/brand/logo-vertical.svg',
  symbol: '/brand/fleetops-symbol.svg',
  mono: '/brand/logo-mono.svg',
  light: '/brand/logo-light.svg',
}

export default function BrandLogo({
  variant = 'horizontal',
  className = '',
  alt = 'FleetOps',
}) {
  const src = VARIANTS[variant] || VARIANTS.horizontal
  return (
    <img
      src={src}
      alt={alt}
      className={`brand-logo brand-logo-${variant} ${className}`.trim()}
      draggable={false}
    />
  )
}
