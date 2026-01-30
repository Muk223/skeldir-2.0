import { Navigation } from "@/components/layout/Navigation";
import { HeroSection } from "@/components/layout/HeroSection";
import { HeroBackgroundGate } from "@/components/layout/HeroBackgroundGate";
import { PartnerLogos } from "@/components/layout/PartnerLogos";
import { ProblemStatement } from "@/components/layout/ProblemStatement";
import { SolutionOverview } from "@/components/layout/SolutionOverview";
import { HowItWorks } from "@/components/layout/HowItWorks";
import { PricingTiers } from "@/components/layout/PricingTiers";
import { TestimonialCarousel } from "@/components/layout/TestimonialCarousel";
import { InteractiveDemo } from "@/components/layout/InteractiveDemo";
import { FinalCTA } from "@/components/layout/FinalCTA";
import { Footer } from "@/components/layout/Footer";

export default function Home() {
  return (
    <main className="min-h-screen flex flex-col font-sans">
      {/* Hero Section: background image gated until loaded to prevent roll-down effect */}
      <HeroBackgroundGate>
        {/* Subtle overlay for text contrast (WCAG AA compliance) */}
        <div
          className="absolute inset-0 -z-10"
          style={{
            backgroundColor: "rgba(0, 0, 0, 0.15)",
          }}
        />

        {/* Sticky Navigation */}
        <Navigation />

        {/* Hero Content Section */}
        <section className="relative flex flex-col overflow-hidden flex-1">
          {/* Hero Content */}
          <HeroSection />

          {/* Partner Logos */}
          <div className="container mx-auto px-4 md:px-6 pb-16 lg:pb-24 partner-logos-section">
            {/* Section Label */}
            <div
              className="partner-logos-label"
              style={{
                fontFamily: 'Inter, sans-serif',
                fontSize: '14px',
                fontWeight: 400,
                lineHeight: 1.4,
                color: '#6C757D',
                textAlign: 'center',
                letterSpacing: '0.02em',
                maxWidth: '700px',
                margin: '0 auto',
                transform: 'translateY(50px)',
              }}
            >
              Trusted by agencies and brands managing $50M+ in annual ad spend
            </div>
            <PartnerLogos />
          </div>

          <style>{`
            @media (max-width: 767px) {
              .partner-logos-section {
                padding-left: 16px !important;
                padding-right: 16px !important;
              }

              .partner-logos-label {
                font-size: 13px !important;
                line-height: 1.5 !important;
                margin-bottom: 24px !important;
                transform: translateY(0) !important;
                padding: 0 16px !important;
              }

              .partner-logos-container {
                margin-top: 0 !important;
              }
            }
          `}</style>
        </section>
      </HeroBackgroundGate>

      {/* Problem Statement Section */}
      <ProblemStatement />

      {/* Solution Overview Section */}
      <SolutionOverview />

      {/* Interactive Product Demo Section */}
      <InteractiveDemo />

      {/* How It Works Timeline Section */}
      <HowItWorks />

      {/* Pricing Tiers Section */}
      <PricingTiers />

      {/* Testimonial Carousel Section */}
      <TestimonialCarousel />

      {/* Final CTA Section - Homepage Conversion Finale */}
      <FinalCTA />

      {/* Footer Section */}
      <Footer />
    </main>
  );
}
