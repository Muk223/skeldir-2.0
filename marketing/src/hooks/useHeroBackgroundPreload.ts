"use client";

import { useEffect, useState } from "react";

/**
 * Preloads a hero background image and reports when it is ready to paint.
 * Prevents the "roll down" effect by ensuring we only apply backgroundImage
 * after the image has loaded (and decoded), so the browser paints it in one pass.
 *
 * @param imageUrl - Absolute path to the hero background image (e.g. /images/Background-2.png)
 * @returns { isReady: boolean } - true once the image has loaded (or was already cached)
 */
export function useHeroBackgroundPreload(imageUrl: string): { isReady: boolean } {
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    if (!imageUrl) {
      setIsReady(false);
      return;
    }

    const img = new Image();

    const onLoad = () => setIsReady(true);
    const onError = () => setIsReady(false);

    img.addEventListener("load", onLoad);
    img.addEventListener("error", onError);

    img.src = imageUrl;

    // If the image is already cached, the browser may not fire 'load' again.
    if (img.complete && img.naturalWidth > 0) {
      setIsReady(true);
    }

    return () => {
      img.removeEventListener("load", onLoad);
      img.removeEventListener("error", onError);
      img.src = "";
    };
  }, [imageUrl]);

  return { isReady };
}
