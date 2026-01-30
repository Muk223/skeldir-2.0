"use client";

import { useHeroBackgroundPreload } from "@/hooks/useHeroBackgroundPreload";

const HOME_HERO_IMAGE = "/images/Background-2.png";
const HERO_FALLBACK_COLOR = "#1e293b";

type HeroBackgroundGateProps = {
  children: React.ReactNode;
};

/**
 * Wraps the homepage hero area and only applies the background image once it has
 * loaded. Shows a solid fallback color until then so the hero doesn't "roll"
 * as the image progressively decodes. Preload links in the document head start
 * the fetch early; this component gates painting until the image is ready.
 */
export function HeroBackgroundGate({ children }: HeroBackgroundGateProps) {
  const { isReady } = useHeroBackgroundPreload(HOME_HERO_IMAGE);

  return (
    <div
      className="relative flex flex-col"
      style={{
        backgroundImage: isReady ? `url(${HOME_HERO_IMAGE})` : undefined,
        backgroundColor: HERO_FALLBACK_COLOR,
        backgroundSize: "cover",
        backgroundPosition: "center top",
        backgroundRepeat: "no-repeat",
        minHeight: "100vh",
      }}
    >
      {children}
    </div>
  );
}
