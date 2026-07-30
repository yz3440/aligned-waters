import { useEffect, useRef, useState } from "react";

import { type ImageWithUser } from "@/types";
import DeskSetupImage from "@/components/DeskSetupImage";

export default function App() {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [isSafari, setIsSafari] = useState(false);
  const [images, setImages] = useState<ImageWithUser[] | null>(null);

  // Pre-joined, pre-sorted (ascending by created_at) at generation time.
  useEffect(() => {
    void fetch("/data/images.json")
      .then((res) => res.json())
      .then((data: ImageWithUser[]) => setImages(data));
  }, []);

  // Detect Safari browser
  useEffect(() => {
    const userAgent = navigator.userAgent;
    const isSafariBrowser = /^((?!chrome|android).)*safari/i.test(userAgent);
    setIsSafari(isSafariBrowser);
  }, []);

  useEffect(() => {
    const autoScrollSpeed = new URLSearchParams(window.location.search).get(
      "autoScrollSpeed",
    );

    if (!autoScrollSpeed || !scrollContainerRef.current) {
      return;
    }

    const speed = parseFloat(autoScrollSpeed);
    if (isNaN(speed) || speed <= 0) {
      return;
    }

    const container = scrollContainerRef.current;
    let animationId: number;

    const scroll = () => {
      container.scrollLeft += speed;

      // Reset to beginning when reached the end
      if (
        container.scrollLeft >=
        container.scrollWidth - container.clientWidth
      ) {
        container.scrollLeft = 0;
      }

      animationId = requestAnimationFrame(scroll);
    };

    animationId = requestAnimationFrame(scroll);

    return () => {
      if (animationId) {
        cancelAnimationFrame(animationId);
      }
    };
  }, [images]);

  return (
    <main
      className="relative min-h-screen"
      style={{
        backgroundImage:
          "linear-gradient(to bottom, #abdbff 0%, #abdbff 45%, #57748a 55%, #57748a 100%)",
        backgroundSize: "cover",
        backgroundPosition: "center",
      }}
    >
      {/* Main content */}
      {!isSafari && images && (
        <div className="flex min-h-screen flex-col items-center justify-center">
          <div className="flex w-full justify-start">
            <div
              ref={scrollContainerRef}
              className="flex min-h-screen items-center overflow-x-auto pb-4"
            >
              {images.map((image) => (
                <div className="relative" key={image.id}>
                  <DeskSetupImage imageWithUser={image} />
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {isSafari && (
        <div className="flex min-h-screen flex-col items-center justify-center">
          <h1 className="text-2xl font-bold">Safari is not supported</h1>
          <p className="">
            Sorry! These images are not displayed correctly in Safari.
          </p>
          <p className="">Please use a different browser to view this page.</p>
        </div>
      )}
    </main>
  );
}
