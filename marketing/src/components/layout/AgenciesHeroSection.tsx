"use client";

import Link from "next/link";
import Image from "next/image";
import { useHeroBackgroundPreload } from "@/hooks/useHeroBackgroundPreload";

const AGENCIES_HERO_IMAGE = "/images/Background 2 Agencies.png";
const AGENCIES_HERO_FALLBACK_COLOR = "#1e293b";

export function AgenciesHeroSection() {
  const { isReady } = useHeroBackgroundPreload(AGENCIES_HERO_IMAGE);

  return (
    <section
      className="agencies-hero"
      aria-labelledby="agencies-hero-heading"
      style={{
        position: "relative",
        width: "100%",
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        ["--agencies-hero-zoom" as string]: "0.82",
        backgroundImage: isReady ? `url("${AGENCIES_HERO_IMAGE}")` : undefined,
        backgroundColor: AGENCIES_HERO_FALLBACK_COLOR,
        backgroundSize: "cover",
        backgroundPosition: "center",
        backgroundRepeat: "no-repeat",
        overflow: "hidden",
        paddingTop: "6rem",
        paddingBottom: "3rem",
      }}
    >
      {/* Exaggerated zoom-out for Agencies hero only: scaled content so more viewport/background is visible */}
      <div
        className="agencies-hero-scaled"
        style={{
          width: '100%',
          maxWidth: '80rem',
          margin: '0 auto',
          padding: '0 1rem',
          transform: 'scale(var(--agencies-hero-zoom, 0.82))',
          transformOrigin: 'center center',
        }}
      >
      <div
        className="agencies-hero-container"
        style={{
          width: '100%',
        }}
      >
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr',
            gap: '3rem',
            alignItems: 'center',
          }}
          className="agencies-hero-grid"
        >
          {/* Left Column: Text Content */}
          <div
            className="agencies-hero-text"
            style={{
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'center',
              textAlign: 'center',
              marginTop: '-12.5rem',
              marginLeft: '-10%',
            }}
          >
          <h1
            id="agencies-hero-heading"
            className="agencies-hero-headline"
            style={{
              fontFamily: "'DM Sans', 'Inter', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
              fontSize: '3.5rem',
              fontWeight: 700,
              lineHeight: 1.15,
              letterSpacing: '-0.025em',
              color: '#111827',
              margin: '0 0 2rem 0',
            }}
          >
            <span style={{ color: '#FFFFFF' }}>Enterprise Attribution Intelligence Without</span> Enterprise Complexity
          </h1>

          <p
            className="agencies-hero-subheadline"
            style={{
              fontFamily: "'DM Sans', 'Inter', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
              fontSize: '1.25rem',
              fontWeight: 400,
              lineHeight: 1.6,
              color: '#FFFFFF',
              margin: '0 auto 2rem auto',
              maxWidth: '37.5rem',
            }}
          >
            Skeldir delivers Bayesian confidence ranges for multi-client portfolios—exposing platform over-reporting discrepancies, eliminating manual reconciliation cycles, with deployment measured in days instead of months.
          </p>

          {/* Feature Badges */}
          <div
            className="agencies-hero-badges"
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: '0.75rem',
              margin: '0 0 2rem 0',
            }}
          >
            {['Multi-tenant Dashboard', 'White-label Branding', 'REST API Access'].map((badge, index) => (
              <span
                key={badge}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.5rem 1rem',
                  borderRadius: '999px',
                  backgroundColor: '#FFFFFF',
                  border: '1px solid #E5E7EB',
                  fontFamily: "'DM Sans', 'Inter', sans-serif",
                  fontSize: '0.875rem',
                  fontWeight: 500,
                  color: '#374151',
                }}
              >
                <svg width="20" height="20" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ flexShrink: 0, marginTop: "2px" }}>
                  <defs>
                    <linearGradient id={`arrowGradientBadge${index}`} x1="0%" y1="0%" x2="100%" y2="100%" gradientUnits="userSpaceOnUse">
                      <stop offset="0%" stopColor="#4F46E5" />
                      <stop offset="50%" stopColor="#A855F7" />
                      <stop offset="100%" stopColor="#EC4899" />
                    </linearGradient>
                  </defs>
                  <path d="M4 3L8 6L4 9" stroke={`url(#arrowGradientBadge${index})`} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
                </svg>
                {badge}
              </span>
            ))}
          </div>

          {/* Primary CTA */}
          <div
            className="agencies-hero-cta"
            style={{
              display: 'flex',
              flexDirection: 'row',
              alignItems: 'center',
              gap: '16px',
            }}
          >
            <Link
              href="/contact-sales?tier=3&source=agencies-hero"
              className="agencies-hero-cta-button"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '0 2rem',
                height: '3.25rem',
                minWidth: '11.25rem',
                backgroundColor: '#2563EB',
                color: '#FFFFFF',
                fontFamily: "'DM Sans', 'Inter', sans-serif",
                fontSize: '1rem',
                fontWeight: 600,
                borderRadius: '0.625rem',
                textDecoration: 'none',
                boxShadow: '0 2px 8px rgba(37, 99, 235, 0.25)',
                transition: 'all 200ms ease',
                cursor: 'pointer',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = '#1D4ED8';
                e.currentTarget.style.boxShadow = '0 4px 16px rgba(37, 99, 235, 0.4)';
                e.currentTarget.style.transform = 'translateY(-1px)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = '#2563EB';
                e.currentTarget.style.boxShadow = '0 2px 8px rgba(37, 99, 235, 0.25)';
                e.currentTarget.style.transform = 'translateY(0)';
              }}
            >
              Book Demo
            </Link>
            <Link
              href="/pricing"
              className="agencies-hero-cta-button-secondary"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                minWidth: '10rem',
                height: '3.5rem',
                padding: '0 1.625rem',
                borderRadius: '999px',
                border: '2px solid #000000',
                color: '#000000',
                background: 'transparent',
                fontFamily: "'DM Sans', 'Inter', sans-serif",
                fontSize: '1rem',
                fontWeight: 600,
                textDecoration: 'none',
                cursor: 'pointer',
                transition: 'all 180ms ease-out',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'rgba(0, 0, 0, 0.1)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'transparent';
              }}
            >
              View Pricing
            </Link>
          </div>
        </div>

          {/* Right Column: Product Visual */}
          <div className="relative mx-auto w-full max-w-[1600px] lg:ml-[45%] agencies-hero-visual" style={{ marginTop: '-15.625rem' }}>
            <div 
              className="relative rounded-2xl overflow-visible agencies-hero-image-glass"
              style={{
                background: 'rgba(255, 255, 255, 0.7)',
                backdropFilter: 'blur(20px) saturate(180%)',
                WebkitBackdropFilter: 'blur(20px) saturate(180%)',
                border: '1px solid rgba(255, 255, 255, 0.3)',
                boxShadow: '0 8px 32px 0 rgba(31, 38, 135, 0.15), 0 0 0 1px rgba(255, 255, 255, 0.2) inset, 0 20px 60px -15px rgba(0, 0, 0, 0.2)',
                transform: 'scale(1.4)',
              }}
            >
              <div className="overflow-hidden rounded-2xl">
                <Image
                  src="/images/Final Agency Hero Image.png"
                  alt="Agency Command Center Dashboard"
                  width={1600}
                  height={1200}
                  className="w-full h-auto object-contain agencies-hero-dashboard-image"
                  priority
                />
              </div>
            </div>
          </div>
        </div>
      </div>
      </div>

      {/* Bottom gradient overlay for transition feel */}
      <div
        className="agencies-hero-bottom-gradient"
        aria-hidden="true"
        style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          height: '16.25rem',
          background:
            'linear-gradient(to bottom, transparent 0%, transparent 40%, rgba(255, 255, 255, 0.4) 65%, rgba(255, 255, 255, 0.85) 85%, rgba(255, 255, 255, 1) 100%)',
          pointerEvents: 'none',
          zIndex: 1,
        }}
      />

      {/* Wave Separator SVG — positioned at bottom for seamless transition */}
      <div
        className="agencies-hero-wave"
        aria-hidden="true"
        style={{
          position: 'absolute',
          bottom: '-7.5rem',
          left: 0,
          right: 0,
          lineHeight: 0,
          overflow: 'hidden',
          zIndex: 2,
        }}
      >
        <svg
          viewBox="0 0 1440 120"
          preserveAspectRatio="none"
          style={{
            display: 'block',
            width: '100%',
            height: '7.5rem',
          }}
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M0,120 C600,-40 840,-40 1440,120 L1440,120 L0,120 Z"
            fill="#FFFFFF"
          />
        </svg>
      </div>

      {/* Responsive Styles */}
      <style>{`
        @keyframes float {
          0%, 100% {
            transform: translateY(0px);
          }
          50% {
            transform: translateY(-0.75rem);
          }
        }
        .agencies-hero-image-glass {
          animation: float 6s ease-in-out infinite;
          position: relative;
        }
        .agencies-hero-image-glass::after {
          content: '';
          position: absolute;
          bottom: -1.5625rem;
          left: 5%;
          right: 5%;
          height: 3.125rem;
          background: radial-gradient(ellipse at center, rgba(0, 0, 0, 0.2) 0%, rgba(0, 0, 0, 0.1) 30%, rgba(0, 0, 0, 0.05) 50%, transparent 75%);
          border-radius: 50%;
          z-index: -1;
          filter: blur(1rem);
          pointer-events: none;
          transform: scale(1.1);
        }

        /* Desktop: 1024px+ — two columns with overlap like home page */
        @media (min-width: 1024px) {
          .agencies-hero-container {
            padding: 0 1.5rem !important;
          }
          .agencies-hero-grid {
            grid-template-columns: 1fr 1fr !important;
            gap: 3rem !important;
          }
          .agencies-hero-text {
            text-align: left !important;
            padding-right: 2rem !important;
            margin-left: -35% !important;
            margin-top: -12.5rem !important;
          }
          .agencies-hero-headline {
            text-align: left !important;
          }
          .agencies-hero-subheadline {
            margin-left: 0 !important;
            margin-right: auto !important;
            text-align: left !important;
          }
          .agencies-hero-badges {
            justify-content: flex-start !important;
          }
          .agencies-hero-cta {
            align-items: flex-start !important;
          }
          .agencies-hero-visual {
            margin-left: 45% !important;
            margin-top: -15.625rem !important;
            max-width: 100rem !important;
          }
          .agencies-hero-image-glass {
            transform: scale(1.4) !important;
          }
        }

        /* Tablet: 768px - 1023px — single column stacked, visual first */
        @media (min-width: 768px) and (max-width: 1023px) {
          .agencies-hero {
            padding-top: 5rem !important;
            min-height: auto !important;
            padding-bottom: 3.5rem !important;
          }
          .agencies-hero-container {
            padding: 0 1.5rem !important;
          }
          .agencies-hero-grid {
            grid-template-columns: 1fr !important;
            gap: 3rem !important;
          }
          .agencies-hero-text {
            order: 2 !important;
            text-align: center !important;
          }
          .agencies-hero-visual {
            order: 1 !important;
          }
          .agencies-hero-headline {
            font-size: 2.625rem !important;
            margin-bottom: 1.25rem !important;
          }
          .agencies-hero-subheadline {
            font-size: 1.125rem !important;
            max-width: 100% !important;
          }
          .agencies-hero-image-glass {
            transform: scale(1.3) !important;
          }
        }

        /* Mobile: < 768px — Revert zoom/alignment so mobile stays as before (no scale) */
        @media (max-width: 767px) {
          .agencies-hero {
            padding-top: 5rem !important;
            min-height: auto !important;
            padding-bottom: 3rem !important;
            justify-content: flex-start !important;
          }
          .agencies-hero-scaled {
            transform: none !important;
          }
          .agencies-hero-container {
            padding: 0 1.25rem !important;
            max-width: 100% !important;
          }
          .agencies-hero-grid {
            grid-template-columns: 1fr !important;
            gap: 2.5rem !important;
            align-items: flex-start !important;
          }
          .agencies-hero-text {
            order: 1 !important;
            text-align: center !important;
            margin-top: 0 !important;
            margin-left: 0 !important;
            padding: 0 !important;
            width: 100% !important;
            max-width: 100% !important;
          }
          .agencies-hero-visual {
            order: 2 !important;
            margin-top: 0 !important;
            margin-left: 0 !important;
            width: 100% !important;
            max-width: 100% !important;
            padding: 0 !important;
          }
          .agencies-hero-headline {
            font-size: 2.25rem !important;
            line-height: 1.25 !important;
            letter-spacing: -0.03em !important;
            font-weight: 700 !important;
            margin-bottom: 1.25rem !important;
            padding: 0 0.25rem !important;
          }
          .agencies-hero-headline span {
            white-space: normal !important;
            display: inline !important;
          }
          .agencies-hero-subheadline {
            font-size: 1rem !important;
            line-height: 1.6 !important;
            max-width: 100% !important;
            margin-bottom: 1.5rem !important;
            margin-left: auto !important;
            margin-right: auto !important;
            padding: 0 0.25rem !important;
          }
          .agencies-hero-badges {
            gap: 0.625rem !important;
            margin-bottom: 2rem !important;
            justify-content: center !important;
            padding: 0 0.25rem !important;
            flex-wrap: wrap !important;
          }
          .agencies-hero-badges span {
            font-size: 0.8125rem !important;
            padding: 0.625rem 1rem !important;
            min-height: 2.5rem !important;
            display: inline-flex !important;
            align-items: center !important;
          }
          .agencies-hero-cta {
            width: 100% !important;
            flex-direction: column !important;
            align-items: stretch !important;
            padding: 0 0.25rem !important;
            gap: 0.75rem !important;
          }
          .agencies-hero-cta-button,
          .agencies-hero-cta-button-secondary {
            width: 100% !important;
            min-width: unset !important;
            height: 3.5rem !important;
            min-height: 3.5rem !important;
            font-size: 1rem !important;
            font-weight: 600 !important;
            padding: 0 1.5rem !important;
            border-radius: 0.75rem !important;
          }
          .agencies-hero-cta-button {
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3) !important;
          }
          .agencies-hero-cta-button-secondary {
            border-radius: 999px !important;
          }
          .agencies-hero-image-glass {
            transform: scale(1) !important;
            width: 100% !important;
            margin: 0 auto !important;
          }
          .agencies-hero-dashboard-image {
            width: 100% !important;
            height: auto !important;
            object-fit: contain !important;
          }
          .agencies-hero-image-glass::after {
            display: none !important;
          }
        }

        /* Very small screens: 320px - 374px — Enhanced readability */
        @media (max-width: 374px) {
          .agencies-hero-container {
            padding: 0 1rem !important;
          }
          .agencies-hero-headline {
            font-size: 2rem !important;
            line-height: 1.2 !important;
            margin-bottom: 1rem !important;
          }
          .agencies-hero-subheadline {
            font-size: 0.9375rem !important;
            line-height: 1.5 !important;
            margin-bottom: 1.25rem !important;
          }
          .agencies-hero-badges {
            flex-direction: column !important;
            align-items: stretch !important;
            gap: 0.5rem !important;
          }
          .agencies-hero-badges span {
            width: 100% !important;
            justify-content: center !important;
          }
          .agencies-hero-cta-button {
            font-size: 0.9375rem !important;
            padding: 0 1.25rem !important;
          }
        }

        /* Large screens: 1440px+ */
        @media (min-width: 1440px) {
          .agencies-hero-container {
            max-width: 87.5rem !important;
            padding: 0 4rem !important;
          }
        }

        /* Ultra-wide screens: 2560px */
        @media (min-width: 2560px) {
          .agencies-hero-container {
            max-width: 100rem !important;
          }
        }
      `}</style>
    </section>
  );
}
