"use client";

import { Navigation } from "@/components/layout/Navigation";
import { Footer } from "@/components/layout/Footer";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { CheckCircle2 } from "lucide-react";

// Partner logos for book-demo carousel — inherently small logos get larger height so they're legible
const bookDemoPartnerLogos = [
  { name: "Callaway", src: "/images/Callaway_1_transparent.png", height: "2rem" },
  { name: "Fresh Clean Threads", src: "/images/FreshCleanThreads_transparent.png", height: "4.25rem" },
  { name: "NordicTrack", src: "/images/Nordictrack_transparent.png", height: "4.25rem" },
  { name: "bareMinerals", src: "/images/Baremin_transparent.png", height: "4.25rem" },
  { name: "TUMI", src: "/images/TUMI_transparent.png", height: "1.5rem" },
  { name: "Pacsun", src: "/images/Pacsun_transparent.png", height: "2rem" },
];

function BookDemoContent() {
  const searchParams = useSearchParams();
  const isSuccess = searchParams.get("success") === "true";

  return (
    <div className="min-h-screen flex flex-col bg-white">
      <Navigation forceVisible={true} />

      <main className="flex-grow pt-8">
        {/* Hero Section with Split Layout */}
        <section
          className="book-demo-hero-section"
          style={{
            minHeight: "calc(100vh - 5rem)",
            display: "flex",
            alignItems: "flex-start",
            paddingTop: "2.5rem",
            background: "linear-gradient(135deg, #F8FAFC 0%, #FFFFFF 50%, #F1F5F9 100%)",
            position: "relative",
            overflow: "hidden",
          }}
        >
          {/* Subtle background pattern */}
          <div
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundImage: `radial-gradient(circle at 1px 1px, rgba(0,0,0,0.03) 1px, transparent 0)`,
              backgroundSize: "2.5rem 2.5rem",
              pointerEvents: "none",
            }}
          />

          <div
            className="book-demo-container container mx-auto px-4 md:px-6 lg:px-8"
            style={{
              maxWidth: "80rem",
              position: "relative",
              zIndex: 1,
            }}
          >
            <div
              className="book-demo-grid"
              style={{
                display: "grid",
                gridTemplateColumns: "1fr",
                gap: "3rem",
                alignItems: "center",
                padding: "1.25rem 0 5rem",
              }}
            >
              {/* Left Column - Value Proposition */}
              <div
                className="value-prop-column"
                style={{
                  maxWidth: "35rem",
                }}
              >
                {/* Badge — button style, transparent except border and text */}
                <div
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    height: "3.25rem",
                    padding: "0 1.5rem",
                    backgroundColor: "transparent",
                    border: "1px solid #2563EB",
                    borderRadius: "0.625rem",
                    marginBottom: "1.5rem",
                    marginLeft: "-10vw",
                  }}
                >
                  <span
                    style={{
                      fontSize: "1rem",
                      fontWeight: 700,
                      color: "#2563EB",
                      fontFamily: "Inter, sans-serif",
                    }}
                  >
                    DEMO SKELDIR TODAY
                  </span>
                </div>

                {/* Main Headline — exactly 2 lines, no wrapping within either line */}
                <h1
                  style={{
                    fontSize: "clamp(2.25rem, 6.5vw, 3.5rem)",
                    fontWeight: 800,
                    color: "#0F172A",
                    lineHeight: 1.12,
                    marginBottom: "1.5rem",
                    marginLeft: "-10vw",
                    fontFamily: "'DM Sans', sans-serif",
                    letterSpacing: "-0.03em",
                    textAlign: "left",
                  }}
                >
                  <span style={{ display: "block", whiteSpace: "nowrap" }}>Grow faster with intelligence that</span>
                  <span style={{ display: "block", whiteSpace: "nowrap" }}>exposes the truth in your ad data.</span>
                </h1>

                {/* Content below headline — aligned vertically with headline */}
                <div style={{ marginLeft: "-10vw" }}>
                  {/* Subheadline */}
                  <p
                    style={{
                      fontSize: "1.125rem",
                      fontWeight: 400,
                      color: "#64748B",
                      lineHeight: 1.6,
                      marginBottom: "40px",
                      fontFamily: "Inter, sans-serif",
                    }}
                  >
                    Skeldir replaces manual platform exports, spreadsheet reconciliation, and conflicting revenue reports by verifying ad platform claims against actual revenue — giving you statistical confidence ranges that turn guesswork into defensible budget decisions all in one unified dashboard
                  </p>

                  {/* Bullet list (product-hero style) */}
                  <div
                    className="book-demo-bullets"
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      gap: "0.625rem",
                      margin: "0 0 3rem 0",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "flex-start", gap: "0.625rem" }}>
                      <svg width="20" height="20" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ flexShrink: 0, marginTop: "2px" }}>
                        <defs>
                          <linearGradient id="book-demo-arrow-1" x1="0%" y1="0%" x2="100%" y2="100%" gradientUnits="userSpaceOnUse">
                            <stop offset="0%" stopColor="#4F46E5" />
                            <stop offset="50%" stopColor="#A855F7" />
                            <stop offset="100%" stopColor="#EC4899" />
                          </linearGradient>
                        </defs>
                        <path d="M4 3L8 6L4 9" stroke="url(#book-demo-arrow-1)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
                      </svg>
                      <span style={{ fontSize: "1.125rem", lineHeight: 1.45, color: "#4B5563", fontFamily: "Inter, sans-serif" }}>
                        Know which ads actually drive revenue, not just clicks
                      </span>
                    </div>
                    <div style={{ display: "flex", alignItems: "flex-start", gap: "0.625rem" }}>
                      <svg width="20" height="20" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ flexShrink: 0, marginTop: "2px" }}>
                        <defs>
                          <linearGradient id="book-demo-arrow-2" x1="0%" y1="0%" x2="100%" y2="100%" gradientUnits="userSpaceOnUse">
                            <stop offset="0%" stopColor="#4F46E5" />
                            <stop offset="50%" stopColor="#A855F7" />
                            <stop offset="100%" stopColor="#EC4899" />
                          </linearGradient>
                        </defs>
                        <path d="M4 3L8 6L4 9" stroke="url(#book-demo-arrow-2)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
                      </svg>
                      <span style={{ fontSize: "1.125rem", lineHeight: 1.45, color: "#4B5563", fontFamily: "Inter, sans-serif" }}>
                        One dashboard to manage all your clients without technical expertise
                      </span>
                    </div>
                    <div style={{ display: "flex", alignItems: "flex-start", gap: "0.625rem" }}>
                      <svg width="20" height="20" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ flexShrink: 0, marginTop: "2px" }}>
                        <defs>
                          <linearGradient id="book-demo-arrow-3" x1="0%" y1="0%" x2="100%" y2="100%" gradientUnits="userSpaceOnUse">
                            <stop offset="0%" stopColor="#4F46E5" />
                            <stop offset="50%" stopColor="#A855F7" />
                            <stop offset="100%" stopColor="#EC4899" />
                          </linearGradient>
                        </defs>
                        <path d="M4 3L8 6L4 9" stroke="url(#book-demo-arrow-3)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
                      </svg>
                      <span style={{ fontSize: "1.125rem", lineHeight: 1.45, color: "#4B5563", fontFamily: "Inter, sans-serif" }}>
                        Reliable numbers backed by your actual sales data
                      </span>
                    </div>
                    <div style={{ display: "flex", alignItems: "flex-start", gap: "0.625rem" }}>
                      <svg width="20" height="20" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ flexShrink: 0, marginTop: "2px" }}>
                        <defs>
                          <linearGradient id="book-demo-arrow-4" x1="0%" y1="0%" x2="100%" y2="100%" gradientUnits="userSpaceOnUse">
                            <stop offset="0%" stopColor="#4F46E5" />
                            <stop offset="50%" stopColor="#A855F7" />
                            <stop offset="100%" stopColor="#EC4899" />
                          </linearGradient>
                        </defs>
                        <path d="M4 3L8 6L4 9" stroke="url(#book-demo-arrow-4)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
                      </svg>
                      <span style={{ fontSize: "1.125rem", lineHeight: 1.45, color: "#4B5563", fontFamily: "Inter, sans-serif" }}>
                        Deploy for new clients faster than your competitors can send a proposal
                      </span>
                    </div>
                  </div>

                  {/* Trust Indicators — smaller partner logo carousel */}
                  <div>
                    <div
                      className="trust-logos book-demo-partner-logos-container"
                      style={{
                        width: "100%",
                        overflow: "hidden",
                        position: "relative",
                      }}
                    >
                      <div className="book-demo-logo-carousel-track">
                        {[...bookDemoPartnerLogos, ...bookDemoPartnerLogos].map((logo, index) => (
                          <img
                            key={`${logo.name}-${index}`}
                            src={logo.src}
                            alt={logo.name}
                            style={{
                              height: logo.height,
                              width: "auto",
                              maxWidth: "8.75rem",
                              objectFit: "contain",
                              filter: "grayscale(100%)",
                              opacity: 0.7,
                              flexShrink: 0,
                            }}
                          />
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Right Column - Form Card */}
              <div
                className="form-column"
                style={{
                  width: "100%",
                  maxWidth: "30rem",
                  justifySelf: "end",
                }}
              >
                <div
                  style={{
                    backgroundColor: "rgba(255, 255, 255, 0.35)",
                    borderRadius: "1.25rem",
                    padding: "2.5rem",
                    boxShadow: "0 2px 12px rgba(0, 0, 0, 0.03)",
                    border: "1px solid rgba(0, 0, 0, 0.06)",
                    backdropFilter: "blur(8px)",
                  }}
                >
                  {isSuccess ? (
                    /* Success State */
                    <div
                      style={{
                        textAlign: "center",
                        padding: "2.5rem 1.25rem",
                      }}
                    >
                      <div
                        style={{
                          width: "4.5rem",
                          height: "4.5rem",
                          backgroundColor: "rgba(34, 197, 94, 0.1)",
                          borderRadius: "50%",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          margin: "0 auto 1.5rem",
                        }}
                      >
                        <CheckCircle2 size={36} color="#22C55E" />
                      </div>
                      <h2
                        style={{
                          fontSize: "1.5rem",
                          fontWeight: 700,
                          color: "#0F172A",
                          marginBottom: "0.75rem",
                          fontFamily: "'DM Sans', sans-serif",
                        }}
                      >
                        Request Received
                      </h2>
                      <p
                        style={{
                          fontSize: "1rem",
                          color: "#64748B",
                          lineHeight: 1.6,
                          marginBottom: "2rem",
                          fontFamily: "Inter, sans-serif",
                        }}
                      >
                        We'll contact you within 24 hours to schedule your personalized
                        strategy session.
                      </p>
                      <div
                        style={{
                          padding: "1rem 1.25rem",
                          backgroundColor: "#F8FAFC",
                          borderRadius: "0.75rem",
                          border: "1px solid #E2E8F0",
                        }}
                      >
                        <p
                          style={{
                            fontSize: "0.875rem",
                            color: "#64748B",
                            fontFamily: "Inter, sans-serif",
                          }}
                        >
                          Questions in the meantime?
                        </p>
                        <a
                          href="mailto:info@synergyscape.io"
                          style={{
                            fontSize: "0.9375rem",
                            fontWeight: 600,
                            color: "#2563EB",
                            textDecoration: "none",
                            fontFamily: "Inter, sans-serif",
                          }}
                        >
                          info@synergyscape.io
                        </a>
                      </div>
                    </div>
                  ) : (
                    /* Form State */
                    <>
                      {/* Form Header */}
                      <div style={{ marginBottom: "2rem" }}>
                        <h2
                          style={{
                            fontSize: "1.5rem",
                            fontWeight: 700,
                            color: "#0F172A",
                            marginBottom: "0.5rem",
                            fontFamily: "'DM Sans', sans-serif",
                          }}
                        >
                          Tell us about your business
                        </h2>
                        <p
                          style={{
                            fontSize: "0.9375rem",
                            color: "#64748B",
                            fontFamily: "Inter, sans-serif",
                          }}
                        >
                          Get a personalized demo of our attribution platform.
                        </p>
                      </div>

                      {/* Netlify Form */}
                      <form
                        name="skeldir-demo-request"
                        method="POST"
                        action="/book-demo/?success=true"
                        data-netlify="true"
                        data-netlify-honeypot="bot-field"
                      >
                        {/* Hidden field for Netlify form detection */}
                        <input type="hidden" name="form-name" value="skeldir-demo-request" />

                        {/* Honeypot field for spam prevention */}
                        <p style={{ display: "none" }}>
                          <label>
                            Don't fill this out if you're human:
                            <input name="bot-field" />
                          </label>
                        </p>

                        {/* Name Row */}
                        <div
                          style={{
                            display: "grid",
                            gridTemplateColumns: "1fr 1fr",
                            gap: "1rem",
                            marginBottom: "1rem",
                          }}
                        >
                          {/* First Name */}
                          <div>
                            <label
                              htmlFor="first-name"
                              style={{
                                display: "block",
                                fontSize: "0.875rem",
                                fontWeight: 500,
                                color: "#374151",
                                marginBottom: "0.375rem",
                                fontFamily: "Inter, sans-serif",
                              }}
                            >
                              First Name
                            </label>
                            <input
                              type="text"
                              id="first-name"
                              name="first-name"
                              required
                              placeholder="Jane"
                              style={{
                                width: "100%",
                                height: "2.875rem",
                                padding: "0 0.875rem",
                                fontSize: "0.9375rem",
                                fontFamily: "Inter, sans-serif",
                                border: "1px solid #D1D5DB",
                                borderRadius: "0.5rem",
                                backgroundColor: "#FFFFFF",
                                color: "#0F172A",
                                outline: "none",
                                transition: "border-color 150ms ease, box-shadow 150ms ease",
                              }}
                              onFocus={(e) => {
                                e.currentTarget.style.borderColor = "#2563EB";
                                e.currentTarget.style.boxShadow = "0 0 0 3px rgba(37, 99, 235, 0.15)";
                              }}
                              onBlur={(e) => {
                                e.currentTarget.style.borderColor = "#D1D5DB";
                                e.currentTarget.style.boxShadow = "none";
                              }}
                            />
                          </div>

                          {/* Last Name */}
                          <div>
                            <label
                              htmlFor="last-name"
                              style={{
                                display: "block",
                                fontSize: "0.875rem",
                                fontWeight: 500,
                                color: "#374151",
                                marginBottom: "0.375rem",
                                fontFamily: "Inter, sans-serif",
                              }}
                            >
                              Last Name
                            </label>
                            <input
                              type="text"
                              id="last-name"
                              name="last-name"
                              required
                              placeholder="Smith"
                              style={{
                                width: "100%",
                                height: "2.875rem",
                                padding: "0 0.875rem",
                                fontSize: "0.9375rem",
                                fontFamily: "Inter, sans-serif",
                                border: "1px solid #D1D5DB",
                                borderRadius: "0.5rem",
                                backgroundColor: "#FFFFFF",
                                color: "#0F172A",
                                outline: "none",
                                transition: "border-color 150ms ease, box-shadow 150ms ease",
                              }}
                              onFocus={(e) => {
                                e.currentTarget.style.borderColor = "#2563EB";
                                e.currentTarget.style.boxShadow = "0 0 0 3px rgba(37, 99, 235, 0.15)";
                              }}
                              onBlur={(e) => {
                                e.currentTarget.style.borderColor = "#D1D5DB";
                                e.currentTarget.style.boxShadow = "none";
                              }}
                            />
                          </div>
                        </div>

                        {/* Work Email */}
                        <div style={{ marginBottom: "16px" }}>
                          <label
                            htmlFor="work-email"
                            style={{
                              display: "block",
                              fontSize: "0.875rem",
                              fontWeight: 500,
                              color: "#374151",
                              marginBottom: "6px",
                              fontFamily: "Inter, sans-serif",
                            }}
                          >
                            Work Email
                          </label>
                          <input
                            type="email"
                            id="work-email"
                            name="work-email"
                            required
                            placeholder="jane@company.com"
                            style={{
                              width: "100%",
                              height: "2.875rem",
                              padding: "0 0.875rem",
                              fontSize: "0.9375rem",
                              fontFamily: "Inter, sans-serif",
                              border: "1px solid #D1D5DB",
                              borderRadius: "8px",
                              backgroundColor: "#FFFFFF",
                              color: "#0F172A",
                              outline: "none",
                              transition: "border-color 150ms ease, box-shadow 150ms ease",
                            }}
                            onFocus={(e) => {
                              e.currentTarget.style.borderColor = "#2563EB";
                              e.currentTarget.style.boxShadow = "0 0 0 3px rgba(37, 99, 235, 0.15)";
                            }}
                            onBlur={(e) => {
                              e.currentTarget.style.borderColor = "#D1D5DB";
                              e.currentTarget.style.boxShadow = "none";
                            }}
                          />
                        </div>

                        {/* Company Name */}
                        <div style={{ marginBottom: "16px" }}>
                          <label
                            htmlFor="company-name"
                            style={{
                              display: "block",
                              fontSize: "0.875rem",
                              fontWeight: 500,
                              color: "#374151",
                              marginBottom: "6px",
                              fontFamily: "Inter, sans-serif",
                            }}
                          >
                            Company Name
                          </label>
                          <input
                            type="text"
                            id="company-name"
                            name="company-name"
                            required
                            placeholder="Acme Inc."
                            style={{
                              width: "100%",
                              height: "2.875rem",
                              padding: "0 0.875rem",
                              fontSize: "0.9375rem",
                              fontFamily: "Inter, sans-serif",
                              border: "1px solid #D1D5DB",
                              borderRadius: "8px",
                              backgroundColor: "#FFFFFF",
                              color: "#0F172A",
                              outline: "none",
                              transition: "border-color 150ms ease, box-shadow 150ms ease",
                            }}
                            onFocus={(e) => {
                              e.currentTarget.style.borderColor = "#2563EB";
                              e.currentTarget.style.boxShadow = "0 0 0 3px rgba(37, 99, 235, 0.15)";
                            }}
                            onBlur={(e) => {
                              e.currentTarget.style.borderColor = "#D1D5DB";
                              e.currentTarget.style.boxShadow = "none";
                            }}
                          />
                        </div>

                        {/* Monthly Ad Spend */}
                        <div style={{ marginBottom: "16px" }}>
                          <label
                            htmlFor="monthly-ad-spend"
                            style={{
                              display: "block",
                              fontSize: "0.875rem",
                              fontWeight: 500,
                              color: "#374151",
                              marginBottom: "6px",
                              fontFamily: "Inter, sans-serif",
                            }}
                          >
                            Monthly Ad Spend
                          </label>
                          <select
                            id="monthly-ad-spend"
                            name="monthly-ad-spend"
                            required
                            defaultValue=""
                            style={{
                              width: "100%",
                              height: "2.875rem",
                              padding: "0 0.875rem",
                              fontSize: "0.9375rem",
                              fontFamily: "Inter, sans-serif",
                              border: "1px solid #D1D5DB",
                              borderRadius: "8px",
                              backgroundColor: "#FFFFFF",
                              color: "#0F172A",
                              outline: "none",
                              cursor: "pointer",
                              appearance: "none",
                              backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%2364748B' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E")`,
                              backgroundRepeat: "no-repeat",
                              backgroundPosition: "right 0.875rem center",
                              paddingRight: "2.5rem",
                              transition: "border-color 150ms ease, box-shadow 150ms ease",
                            }}
                            onFocus={(e) => {
                              e.currentTarget.style.borderColor = "#2563EB";
                              e.currentTarget.style.boxShadow = "0 0 0 3px rgba(37, 99, 235, 0.15)";
                            }}
                            onBlur={(e) => {
                              e.currentTarget.style.borderColor = "#D1D5DB";
                              e.currentTarget.style.boxShadow = "none";
                            }}
                          >
                            <option value="" disabled>
                              Select your monthly spend
                            </option>
                            <option value="<$50K">&lt;$50K</option>
                            <option value="$50K-$150K">$50K-$150K</option>
                            <option value="$150K-$500K">$150K-$500K</option>
                            <option value="$500K+">$500K+</option>
                          </select>
                        </div>

                        {/* Attribution Challenge */}
                        <div style={{ marginBottom: "16px" }}>
                          <label
                            htmlFor="attribution-challenge"
                            style={{
                              display: "block",
                              fontSize: "0.875rem",
                              fontWeight: 500,
                              color: "#374151",
                              marginBottom: "6px",
                              fontFamily: "Inter, sans-serif",
                            }}
                          >
                            Primary Attribution Challenge
                          </label>
                          <select
                            id="attribution-challenge"
                            name="attribution-challenge"
                            required
                            defaultValue=""
                            style={{
                              width: "100%",
                              height: "2.875rem",
                              padding: "0 0.875rem",
                              fontSize: "0.9375rem",
                              fontFamily: "Inter, sans-serif",
                              border: "1px solid #D1D5DB",
                              borderRadius: "8px",
                              backgroundColor: "#FFFFFF",
                              color: "#0F172A",
                              outline: "none",
                              cursor: "pointer",
                              appearance: "none",
                              backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%2364748B' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E")`,
                              backgroundRepeat: "no-repeat",
                              backgroundPosition: "right 0.875rem center",
                              paddingRight: "2.5rem",
                              transition: "border-color 150ms ease, box-shadow 150ms ease",
                            }}
                            onFocus={(e) => {
                              e.currentTarget.style.borderColor = "#2563EB";
                              e.currentTarget.style.boxShadow = "0 0 0 3px rgba(37, 99, 235, 0.15)";
                            }}
                            onBlur={(e) => {
                              e.currentTarget.style.borderColor = "#D1D5DB";
                              e.currentTarget.style.boxShadow = "none";
                            }}
                          >
                            <option value="" disabled>
                              Select your biggest challenge
                            </option>
                            <option value="Conflicting platform data">Conflicting platform data</option>
                            <option value="Manual reconciliation taking too long">Manual reconciliation taking too long</option>
                            <option value="Don't trust current numbers">Don't trust current numbers</option>
                            <option value="CFO demanding ROI proof">CFO demanding ROI proof</option>
                          </select>
                        </div>

                        {/* Referral Source */}
                        <div style={{ marginBottom: "1.75rem" }}>
                          <label
                            htmlFor="referral-source"
                            style={{
                              display: "block",
                              fontSize: "0.875rem",
                              fontWeight: 500,
                              color: "#374151",
                              marginBottom: "6px",
                              fontFamily: "Inter, sans-serif",
                            }}
                          >
                            How did you hear about us?{" "}
                            <span style={{ color: "#94A3B8", fontWeight: 400 }}>(optional)</span>
                          </label>
                          <select
                            id="referral-source"
                            name="referral-source"
                            defaultValue=""
                            style={{
                              width: "100%",
                              height: "2.875rem",
                              padding: "0 0.875rem",
                              fontSize: "0.9375rem",
                              fontFamily: "Inter, sans-serif",
                              border: "1px solid #D1D5DB",
                              borderRadius: "8px",
                              backgroundColor: "#FFFFFF",
                              color: "#0F172A",
                              outline: "none",
                              cursor: "pointer",
                              appearance: "none",
                              backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%2364748B' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E")`,
                              backgroundRepeat: "no-repeat",
                              backgroundPosition: "right 0.875rem center",
                              paddingRight: "2.5rem",
                              transition: "border-color 150ms ease, box-shadow 150ms ease",
                            }}
                            onFocus={(e) => {
                              e.currentTarget.style.borderColor = "#2563EB";
                              e.currentTarget.style.boxShadow = "0 0 0 3px rgba(37, 99, 235, 0.15)";
                            }}
                            onBlur={(e) => {
                              e.currentTarget.style.borderColor = "#D1D5DB";
                              e.currentTarget.style.boxShadow = "none";
                            }}
                          >
                            <option value="">Select an option</option>
                            <option value="Search">Search</option>
                            <option value="LinkedIn">LinkedIn</option>
                            <option value="Referral">Referral</option>
                            <option value="Agency partner">Agency partner</option>
                            <option value="Other">Other</option>
                          </select>
                        </div>

                        {/* Submit Button */}
                        <button
                          type="submit"
                          style={{
                            width: "100%",
                            height: "3.25rem",
                            backgroundColor: "#2563EB",
                            color: "#FFFFFF",
                            fontSize: "1rem",
                            fontWeight: 700,
                            fontFamily: "Inter, sans-serif",
                            border: "none",
                            borderRadius: "0.625rem",
                            cursor: "pointer",
                            boxShadow: "0 4px 14px rgba(37, 99, 235, 0.35)",
                            transition: "all 200ms ease",
                          }}
                          onMouseEnter={(e) => {
                            e.currentTarget.style.backgroundColor = "#1D4ED8";
                            e.currentTarget.style.boxShadow = "0 6px 20px rgba(37, 99, 235, 0.45)";
                            e.currentTarget.style.transform = "translateY(-1px)";
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.backgroundColor = "#2563EB";
                            e.currentTarget.style.boxShadow = "0 4px 14px rgba(37, 99, 235, 0.35)";
                            e.currentTarget.style.transform = "translateY(0)";
                          }}
                          onMouseDown={(e) => {
                            e.currentTarget.style.transform = "translateY(0)";
                          }}
                        >
                          Book Your Demo
                        </button>

                        {/* Privacy Note */}
                        <p
                          style={{
                            fontSize: "0.75rem",
                            color: "#94A3B8",
                            textAlign: "center",
                            marginTop: "1rem",
                            fontFamily: "Inter, sans-serif",
                            lineHeight: 1.5,
                          }}
                        >
                          By submitting, you agree to our{" "}
                          <a
                            href="/privacy"
                            style={{ color: "#64748B", textDecoration: "underline" }}
                          >
                            Privacy Policy
                          </a>
                          . We'll never share your information.
                        </p>
                      </form>
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>

      <Footer />

      {/* Responsive Styles */}
      <style>{`
        /* Book-demo partner logo carousel (smaller iteration of PartnerLogos) */
        @keyframes book-demo-scroll-logos {
          0% { transform: translateX(0); }
          100% { transform: translateX(-50%); }
        }
        .book-demo-partner-logos-container {
          margin-top: 0;
        }
        .book-demo-logo-carousel-track {
          display: flex;
          align-items: center;
          gap: 2rem;
          animation: book-demo-scroll-logos 35s linear infinite;
          width: max-content;
        }
        .book-demo-logo-carousel-track img {
          flex-shrink: 0;
        }

        /* Desktop Layout (≥1024px) */
        @media (min-width: 1024px) {
          .book-demo-grid {
            grid-template-columns: 55% 45% !important;
            gap: 4rem !important;
            padding: 1.25rem 0 6.25rem !important;
          }

          .value-prop-column {
            max-width: 560px !important;
          }

          .form-column {
            max-width: 30rem !important;
            justify-self: end !important;
          }
        }

        /* Large Desktop (≥1280px) */
        @media (min-width: 1280px) {
          .book-demo-grid {
            gap: 80px !important;
          }
        }

        /* Tablet (768px - 1023px) */
        @media (min-width: 768px) and (max-width: 1023px) {
          .book-demo-grid {
            grid-template-columns: 1fr !important;
            gap: 3rem !important;
            padding: 1.25rem 0 5rem !important;
          }

          .value-prop-column {
            max-width: 100% !important;
            text-align: center !important;
          }

          .value-prop-column > div:first-child {
            display: flex !important;
            justify-content: center !important;
          }

          .book-demo-bullets {
            max-width: 31.25rem !important;
            margin-left: auto !important;
            margin-right: auto !important;
          }

          .trust-logos {
            justify-content: center !important;
          }

          .form-column {
            max-width: 520px !important;
            margin: 0 auto !important;
            justify-self: center !important;
          }
        }

        /* Mobile (≤767px) — aligned with rest of site */
        @media (max-width: 767px) {
          .book-demo-hero-section {
            padding-top: 3rem !important;
            min-height: auto !important;
            align-items: flex-start !important;
          }

          .book-demo-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
          }

          .book-demo-grid {
            grid-template-columns: 1fr !important;
            gap: 32px !important;
            padding: 24px 0 48px !important;
          }

          .value-prop-column {
            max-width: 100% !important;
            text-align: center !important;
          }

          .value-prop-column > div:first-child {
            display: flex !important;
            justify-content: center !important;
            margin-left: 0 !important;
          }

          .value-prop-column h1 {
            margin-left: 0 !important;
            text-align: center !important;
          }

          .value-prop-column h1 span {
            white-space: normal !important;
          }

          .value-prop-column h1 + div {
            margin-left: 0 !important;
            text-align: center !important;
          }

          .value-prop-column div:has(.trust-logos) {
            display: none !important;
          }

          .form-column {
            max-width: 100% !important;
            justify-self: center !important;
          }

          .form-column > div {
            padding: 1.5rem 1rem !important;
            border-radius: 1rem !important;
          }

          /* Stack name fields on mobile */
          .form-column form > div:first-of-type {
            grid-template-columns: 1fr !important;
          }
        }

        /* Focus visible for accessibility */
        input:focus-visible,
        select:focus-visible,
        button:focus-visible {
          outline: 2px solid #2563EB !important;
          outline-offset: 2px !important;
        }

        /* Placeholder styling */
        input::placeholder {
          color: #9CA3AF;
        }

        /* Select disabled option styling */
        select option[value=""][disabled] {
          color: #9CA3AF;
        }
      `}</style>
    </div>
  );
}

export default function BookDemoPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-white">
          <div
            style={{
              width: "2.5rem",
              height: "2.5rem",
              border: "3px solid #E5E7EB",
              borderTopColor: "#2563EB",
              borderRadius: "50%",
              animation: "spin 0.8s linear infinite",
            }}
          />
          <style>{`
            @keyframes spin {
              to { transform: rotate(360deg); }
            }
          `}</style>
        </div>
      }
    >
      <BookDemoContent />
    </Suspense>
  );
}
