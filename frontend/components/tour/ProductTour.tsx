"use client";

import { useCallback, useState } from "react";

import { TOUR_SCENES, TourChrome } from "@/components/tour/TourScenes";
import { TOUR_SCENE_COUNT, markTourSeen } from "@/lib/tour";

export function ProductTour({ onClose }: { onClose: () => void }) {
  const [scene, setScene] = useState(0);
  const Scene = TOUR_SCENES[scene];

  const finish = useCallback(() => {
    markTourSeen();
    onClose();
  }, [onClose]);

  return (
    <TourChrome
      scene={scene}
      onNext={() => setScene((current) => Math.min(TOUR_SCENE_COUNT - 1, current + 1))}
      onPrev={() => setScene((current) => Math.max(0, current - 1))}
      onSkip={finish}
      onFinish={finish}
    >
      <Scene />
    </TourChrome>
  );
}
