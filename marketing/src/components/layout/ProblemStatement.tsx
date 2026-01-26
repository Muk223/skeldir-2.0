"use client";

// Icon Components - Large composite illustrations matching reference (96px height)

// Card 1: Platform Over-Reporting - RED and ORANGE overlapping dollar signs
function PlatformOverReportingIcon() {
  return (
    <div
      style={{
        width: "96px",
        height: "96px",
        position: "relative",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
       {/* Amber/Orange circle background */}
       <div
         style={{
           width: "88px",
           height: "88px",
           borderRadius: "50%",
           backgroundColor: "#FEF3C7",
           position: "absolute",
           left: "4px",
           top: "4px",
         }}
       />
       {/* Dollar sign 1 - Back, ORANGE */}
       <span
         style={{
           position: "absolute",
           left: "40px",
           top: "48px",
           fontFamily: "Inter, sans-serif",
           fontSize: "56px",
           fontWeight: 900,
           color: "#F59E0B",
           lineHeight: 1,
           transform: "translate(-50%, -50%)",
         }}
       >$</span>
       {/* Dollar sign 2 - Front, RED (overlapping) */}
       <span
         style={{
           position: "absolute",
           left: "56px",
           top: "48px",
           fontFamily: "Inter, sans-serif",
           fontSize: "56px",
           fontWeight: 900,
           color: "#EF4444",
           lineHeight: 1,
           transform: "translate(-50%, -50%)",
         }}
       >$</span>
    </div>
  );
}

// Card 2: Reconciliation Paralysis - Grid Spreadsheet -> Break -> Grid Spreadsheet (ORANGE)
function ReconciliationParalysisIcon() {
  return (
    <img 
      src="/images/spreadsheet-iteration-2.png" 
      alt="Reconciliation Paralysis" 
      style={{
        width: "auto",
        height: "112px",
        objectFit: "contain",
        display: "block"
      }}
    />
  );
}

// Card 3: Black-Box Distrust - Math symbols + Arrow + Calculator with WHITE ? in DARK box
function BlackBoxDistrustIcon() {
  return (
    <div
      style={{
        width: "auto",
        height: "auto",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: "12px",
      }}
    >
      {/* Distrust icon image */}
      <img 
        src="/images/distrust.png" 
        alt="Distrust" 
        style={{ 
          width: "auto",
          height: "80px",
          objectFit: "contain",
          display: "block"
        }}
      />

      {/* Arrow pointing right */}
      <svg width="80" height="40" viewBox="0 0 32 16" fill="none">
        <line x1="0" y1="8" x2="22" y2="8" stroke="#000000" strokeWidth="5" />
        <polygon points="20,2 32,8 20,14" fill="#000000" />
      </svg>

      {/* Calculator with dark screen and WHITE question mark */}
      <div style={{ position: "relative", width: "120px", height: "150px" }}>
        <img
          src="/images/Calculator.svg"
          alt="Calculator"
          style={{
            width: "120px",
            height: "150px",
            objectFit: "contain",
            filter: "brightness(0)"
          }}
        />
        {/* WHITE Question mark overlay on dark screen */}
        <svg
          width="120"
          height="150"
          viewBox="0 0 56 72"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            pointerEvents: "none"
          }}
        >
          <text
            x="28"
            y="19"
            fontFamily="Inter, sans-serif"
            fontSize="36"
            fontWeight="700"
            fill="white"
            textAnchor="middle"
            dominantBaseline="middle"
          >?</text>
        </svg>
      </div>
    </div>
  );
}

interface ProblemCardProps {
  icon: React.ReactNode;
  headline: string;
  metric: string;
  metricColor: string;
  body: string;
}

function ProblemCard({ icon, headline, metric, metricColor, body }: ProblemCardProps) {
  return (
    <div
      className="problem-card"
      style={{
        padding: "40px",
        border: "1px solid #E9ECEF",
        borderRadius: "12px",
        boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
        backgroundColor: "#FFFFFF",
        display: "flex",
        flexDirection: "column",
        height: "100%",
      }}
    >
      {/* Icon Container - 96px height for visual mass */}
      <div style={{
        marginBottom: "24px",
        height: "96px",
        display: "flex",
        alignItems: "flex-start",
      }}>
        {icon}
      </div>

      {/* Headline */}
      <h3
        style={{
          fontFamily: "Inter, sans-serif",
          fontSize: "20px",
          fontWeight: 600,
          lineHeight: 1.4,
          color: "#212529",
          margin: "0 0 8px 0",
        }}
      >
        {headline}
      </h3>

      {/* Highlight Metric */}
      <p
        style={{
          fontFamily: "Inter, sans-serif",
          fontSize: "16px",
          fontWeight: 700,
          lineHeight: 1.5,
          color: metricColor,
          margin: "0 0 12px 0",
        }}
      >
        {metric}
      </p>

      {/* Body Text */}
      <p
        style={{
          fontFamily: "Inter, sans-serif",
          fontSize: "16px",
          fontWeight: 400,
          lineHeight: 1.5,
          color: "#6C757D",
          margin: 0,
        }}
      >
        {body}
      </p>
    </div>
  );
}

export function ProblemStatement() {
  const problems = [
    {
      icon: <PlatformOverReportingIcon />,
      headline: "Platform Over-Reporting",
      metric: "16-40% of revenue double-claimed",
      metricColor: "#EF4444",
      body: "Google and Meta both claim credit for the same conversion, systematically inflating their performance.",
    },
    {
      icon: <ReconciliationParalysisIcon />,
      headline: "Reconciliation Paralysis",
      metric: "15 hours/week wasted",
      metricColor: "#F59E0B",
      body: "Chasing discrepancies across Google Ads, Meta, Stripe, and Shopify—without a single source of truth",
    },
    {
      icon: <BlackBoxDistrustIcon />,
      headline: "Black-Box Distrust",
      metric: "70% of ad spend decisions rely on unverified platform claims",
      metricColor: "#1E3A8A",
      body: "Uncertain black box numbers stall budget shifts. See exactly when to act with confidence ranges",
    },
  ];

  return (
    <section
      className="problem-statement-section"
      style={{
        backgroundColor: "#FFFFFF",
        paddingTop: "64px",
        paddingBottom: "64px",
        position: "relative",
      }}
    >
      {/* Gradient transition overlay at the top */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: "150px",
          background: "linear-gradient(to bottom, transparent 0%, rgba(255, 255, 255, 0.3) 30%, rgba(255, 255, 255, 0.7) 60%, rgba(255, 255, 255, 1) 100%)",
          pointerEvents: "none",
          zIndex: 1,
        }}
      />
      {/* CSS for responsive grid */}
      <style>
        {`
          .problem-statement-container {
            max-width: 1500px;
            margin: 0 auto;
            padding-left: 48px;
            padding-right: 48px;
          }
          .problem-statement-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 100px;
          }
          @media (max-width: 1024px) {
            .problem-statement-grid {
              grid-template-columns: repeat(2, 1fr);
              gap: 54px;
            }
            .problem-statement-container {
              padding-left: 32px;
              padding-right: 32px;
            }
          }
          @media (max-width: 767px) {
            .problem-statement-section {
              padding-top: 48px !important;
              padding-bottom: 48px !important;
            }

            .problem-statement-container {
              padding-left: 20px;
              padding-right: 20px;
            }
            
            .problem-statement-grid {
              grid-template-columns: 1fr !important;
              gap: 32px !important;
            }

            .problem-statement-title {
              font-size: 32px !important;
              line-height: 1.25 !important;
              margin-bottom: 40px !important;
              padding: 0 16px !important;
            }

            .problem-card {
              padding: 24px !important;
            }

            .problem-card h3 {
              font-size: 18px !important;
              line-height: 1.4 !important;
            }

            .problem-card p {
              font-size: 15px !important;
              line-height: 1.5 !important;
            }
          }
        `}
      </style>

      <div className="problem-statement-container" style={{ position: "relative", zIndex: 2 }}>
        {/* Section Title */}
        <h2
          className="problem-statement-title"
          style={{
            fontFamily: "'Inter', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
            fontSize: "44px",
            fontWeight: 700,
            lineHeight: 1.2,
            letterSpacing: "-0.025em",
            color: "#111827",
            textAlign: "center",
            marginTop: 0,
            marginBottom: "56px",
          }}
        >
          The Attribution Crisis
        </h2>

        {/* 3-Column Grid */}
        <div className="problem-statement-grid">
          {problems.map((problem, index) => (
            <ProblemCard
              key={index}
              icon={problem.icon}
              headline={problem.headline}
              metric={problem.metric}
              metricColor={problem.metricColor}
              body={problem.body}
            />
          ))}
        </div>
      </div>
    </section>
  );
}
