"use client";

// ============================================================================
// FOOTER SECTION
// Reference: Footer (Expected State).png
// Dark navy background, 4-column layout, contact info, social icons
// ============================================================================

export function Footer() {
  const footerLinks = {
    product: {
      title: "PRODUCT",
      links: [
        { label: "Plans", href: "/pricing" },
        { label: "Request Demo", href: "#demo" },
        { label: "Features", href: "#features" },
        { label: "Security", href: "#security" },
        { label: "Status", href: "#status" },
      ],
    },
    company: {
      title: "COMPANY",
      links: [
        { label: "About", href: "#about" },
        { label: "Careers", href: "#careers" },
        { label: "Blog", href: "#blog" },
        { label: "Press", href: "#press" },
      ],
    },
    support: {
      title: "SUPPORT",
      links: [
        { label: "Documentation", href: "#docs" },
        { label: "API Reference", href: "#api" },
        { label: "Status", href: "#status" },
        { label: "Feedback", href: "#feedback" },
      ],
    },
  };

  const legalLinks = [
    { label: "Privacy Policy", href: "#privacy" },
    { label: "Terms of Service", href: "#terms" },
    { label: "GDPR", href: "#gdpr" },
    { label: "Security", href: "#security" },
  ];

  return (
    <footer
      id="footer"
      style={{
        width: "100%",
        backgroundColor: "rgba(11, 13, 60, 1)",
        padding: "100px 40px 60px 40px",
        fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
      }}
    >
      <div
        style={{
          maxWidth: "1200px",
          margin: "0 auto",
        }}
      >
        {/* ================================================================ */}
        {/* MAIN FOOTER CONTENT - Logo + 4 Column Grid                      */}
        {/* ================================================================ */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "200px repeat(4, 1fr)",
            gap: "40px",
            marginBottom: "64px",
          }}
          className="footer-grid"
        >
          {/* Column 0: Logo & Address */}
          <div>
            <img
              src="/images/skeldir-logo-shield-only.png"
              alt="Skeldir Logo"
              style={{
                width: "100%",
                height: "auto",
                maxWidth: "120px",
                marginBottom: "20px",
                marginTop: "-40px",
                marginLeft: "-60px",
              }}
            />
            <address
              style={{
                color: "#FFFFFF",
                fontSize: "14px",
                fontWeight: 400,
                fontStyle: "normal",
                lineHeight: "1.6",
                marginLeft: "-60px",
                marginBottom: "20px",
              }}
            >
              101 South 5th St<br />
              Suite 1401<br />
              Minneapolis, MN 55402<br />
              United States
            </address>

            {/* Social Icons */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "16px",
                marginLeft: "-60px",
              }}
            >
              {/* LinkedIn */}
              <a
                href="https://linkedin.com/company/skeldir"
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  color: "#FFFFFF",
                  transition: "color 200ms ease",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.color = "#FFFFFF";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.color = "#FFFFFF";
                }}
                aria-label="LinkedIn"
              >
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
                </svg>
              </a>

              {/* Twitter/X */}
              <a
                href="https://x.com/skeldir"
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  color: "#FFFFFF",
                  transition: "color 200ms ease",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.color = "#FFFFFF";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.color = "#FFFFFF";
                }}
                aria-label="Twitter"
              >
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
                </svg>
              </a>

              {/* Instagram */}
              <a
                href="https://instagram.com/skeldir"
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  color: "#FFFFFF",
                  transition: "color 200ms ease",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.color = "#FFFFFF";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.color = "#FFFFFF";
                }}
                aria-label="Instagram"
              >
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z" />
                </svg>
              </a>
            </div>
          </div>

          {/* Column 1: Product */}
          <div>
            <h3
              style={{
                color: "#FFFFFF",
                fontSize: "14px",
                fontWeight: 700,
                letterSpacing: "0.05em",
                marginBottom: "20px",
                textTransform: "uppercase",
              }}
            >
              {footerLinks.product.title}
            </h3>
            <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
              {footerLinks.product.links.map((link) => (
                <li key={link.label} style={{ marginBottom: "12px" }}>
                  <a
                    href={link.href}
                    style={{
                      color: "#FFFFFF",
                      fontSize: "14px",
                      fontWeight: 400,
                      textDecoration: "none",
                      transition: "color 200ms ease",
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.color = "#FFFFFF";
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.color = "#FFFFFF";
                    }}
                  >
                    {link.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>

          {/* Column 2: Company */}
          <div>
            <h3
              style={{
                color: "#FFFFFF",
                fontSize: "14px",
                fontWeight: 700,
                letterSpacing: "0.05em",
                marginBottom: "20px",
                textTransform: "uppercase",
              }}
            >
              {footerLinks.company.title}
            </h3>
            <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
              {footerLinks.company.links.map((link) => (
                <li key={link.label} style={{ marginBottom: "12px" }}>
                  <a
                    href={link.href}
                    style={{
                      color: "#FFFFFF",
                      fontSize: "14px",
                      fontWeight: 400,
                      textDecoration: "none",
                      transition: "color 200ms ease",
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.color = "#FFFFFF";
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.color = "#FFFFFF";
                    }}
                  >
                    {link.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>

          {/* Column 3: Support */}
          <div>
            <h3
              style={{
                color: "#FFFFFF",
                fontSize: "14px",
                fontWeight: 700,
                letterSpacing: "0.05em",
                marginBottom: "20px",
                textTransform: "uppercase",
              }}
            >
              {footerLinks.support.title}
            </h3>
            <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
              {footerLinks.support.links.map((link) => (
                <li key={link.label} style={{ marginBottom: "12px" }}>
                  <a
                    href={link.href}
                    style={{
                      color: "#FFFFFF",
                      fontSize: "14px",
                      fontWeight: 400,
                      textDecoration: "none",
                      transition: "color 200ms ease",
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.color = "#FFFFFF";
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.color = "#FFFFFF";
                    }}
                  >
                    {link.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>

          {/* Column 4: Get In Touch */}
          <div>
            <h3
              style={{
                color: "#FFFFFF",
                fontSize: "14px",
                fontWeight: 700,
                letterSpacing: "0.05em",
                marginBottom: "20px",
                textTransform: "uppercase",
              }}
            >
              GET IN TOUCH
            </h3>
            <div style={{ marginBottom: "24px" }}>
              <a
                href="mailto:info@synergyscape.io"
                style={{
                  color: "#FFFFFF",
                  fontSize: "14px",
                  fontWeight: 400,
                  textDecoration: "none",
                  transition: "color 200ms ease",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.color = "#FFFFFF";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.color = "#FFFFFF";
                }}
              >
                info@synergyscape.io
              </a>
            </div>
            <a
              href="/pricing"
              style={{
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                padding: "12px 32px",
                backgroundColor: "transparent",
                color: "#FFFFFF",
                fontSize: "14px",
                fontWeight: 600,
                textDecoration: "none",
                borderRadius: "25px",
                border: "1.5px solid #FFFFFF",
                cursor: "pointer",
                transition: "all 200ms ease",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = "#FFFFFF";
                e.currentTarget.style.color = "#4A5F7F";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = "transparent";
                e.currentTarget.style.color = "#FFFFFF";
              }}
            >
              Book Demo
            </a>
          </div>
        </div>

        {/* ================================================================ */}
        {/* FOOTER BOTTOM - Legal Links, Copyright, Social Icons            */}
        {/* ================================================================ */}
        <div
          style={{
            borderTop: "1px solid rgba(255, 255, 255, 0.1)",
            paddingTop: "40px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: "16px",
          }}
          className="footer-bottom"
        >
          {/* Legal Links */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              flexWrap: "wrap",
            }}
          >
            {legalLinks.map((link, index) => (
              <span key={link.label} style={{ display: "flex", alignItems: "center" }}>
                <a
                  href={link.href}
                  style={{
                    color: "#FFFFFF",
                    fontSize: "12px",
                    fontWeight: 400,
                    textDecoration: "none",
                    transition: "color 200ms ease",
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.color = "#FFFFFF";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.color = "#FFFFFF";
                  }}
                >
                  {link.label}
                </a>
                {index < legalLinks.length - 1 && (
                  <span style={{ color: "#FFFFFF", margin: "0 8px", fontSize: "12px" }}>
                    &bull;
                  </span>
                )}
              </span>
            ))}
          </div>

          {/* Copyright */}
          <div
            style={{
              color: "#FFFFFF",
              fontSize: "12px",
              fontWeight: 400,
            }}
          >
            &copy; 2026 Skeldir, Inc. All rights reserved.
          </div>

          {/* Social Icons */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "16px",
            }}
          >
            {/* LinkedIn */}
            <a
              href="https://linkedin.com/company/skeldir"
              target="_blank"
              rel="noopener noreferrer"
              style={{
                color: "#FFFFFF",
                transition: "color 200ms ease",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.color = "#FFFFFF";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.color = "#FFFFFF";
              }}
              aria-label="LinkedIn"
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="currentColor"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
              </svg>
            </a>

            {/* Twitter/X */}
            <a
              href="https://x.com/skeldir"
              target="_blank"
              rel="noopener noreferrer"
              style={{
                color: "#FFFFFF",
                transition: "color 200ms ease",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.color = "#FFFFFF";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.color = "#FFFFFF";
              }}
              aria-label="Twitter"
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="currentColor"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
              </svg>
            </a>

            {/* Instagram */}
            <a
              href="https://instagram.com/skeldir"
              target="_blank"
              rel="noopener noreferrer"
              style={{
                color: "#FFFFFF",
                transition: "color 200ms ease",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.color = "#FFFFFF";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.color = "#FFFFFF";
              }}
              aria-label="Instagram"
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="currentColor"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z" />
              </svg>
            </a>
          </div>
        </div>
      </div>

      {/* ================================================================== */}
      {/* RESPONSIVE STYLES                                                 */}
      {/* ================================================================== */}
      <style>{`
        /* TABLET (768px - 1024px) */
        @media (max-width: 1024px) and (min-width: 768px) {
          .footer-grid {
            grid-template-columns: 1fr 1fr !important;
            gap: 32px 40px !important;
          }
          
          .footer-grid > div:first-child {
            grid-column: 1 / -1 !important;
            text-align: center !important;
            display: flex !important;
            justify-content: center !important;
          }
        }

        /* MOBILE (≤767px) */
        @media (max-width: 767px) {
          #footer {
            padding: 80px 24px 40px 24px !important;
          }

          .footer-grid {
            grid-template-columns: 1fr !important;
            gap: 32px !important;
            text-align: center !important;
          }

          .footer-grid > div {
            display: flex !important;
            flex-direction: column !important;
            align-items: center !important;
          }

          .footer-bottom {
            flex-direction: column !important;
            text-align: center !important;
            gap: 16px !important;
          }
        }
      `}</style>
    </footer>
  );
}
