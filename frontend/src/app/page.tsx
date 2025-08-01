"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";

import { IMAGES_WITH_USERS } from "@/data/imageWithUser";
import { env } from "@/env";
import DeskSetupImage from "./_components/DeskSetupImage";

import { getHue } from "@/lib/colorUtils";

export default function Home() {
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  const IMAGES = [...IMAGES_WITH_USERS].sort((a, b) => {
    // const aHue = getHue(a.color);
    // const bHue = getHue(b.color);
    // return bHue - aHue;
    return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
  });

  useEffect(() => {
    const scrollContainer = scrollContainerRef.current;
    if (!scrollContainer) return;

    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      // Add a multiplier for smoother scrolling and better responsiveness
      const scrollMultiplier = 1.5;
      scrollContainer.scrollLeft += e.deltaY * scrollMultiplier;
    };

    // Touch event handlers for mobile
    let isScrolling = false;
    let startX = 0;
    let startY = 0;
    let scrollLeft = 0;

    const handleTouchStart = (e: TouchEvent) => {
      if (e.touches.length === 0 || !e.touches[0]) return;
      isScrolling = true;
      startX = e.touches[0].pageX - scrollContainer.offsetLeft;
      startY = e.touches[0].pageY;
      scrollLeft = scrollContainer.scrollLeft;
    };

    const handleTouchMove = (e: TouchEvent) => {
      if (!isScrolling || e.touches.length === 0 || !e.touches[0]) return;

      e.preventDefault();
      const x = e.touches[0].pageX - scrollContainer.offsetLeft;
      const y = e.touches[0].pageY;
      const walkX = (x - startX) * 2; // Scroll speed multiplier
      const walkY = Math.abs(y - startY);

      // Only scroll horizontally if the horizontal movement is greater than vertical
      if (Math.abs(walkX) > walkY) {
        scrollContainer.scrollLeft = scrollLeft - walkX;
      }
    };

    const handleTouchEnd = () => {
      isScrolling = false;
    };

    scrollContainer.addEventListener("wheel", handleWheel, { passive: false });
    scrollContainer.addEventListener("touchstart", handleTouchStart, {
      passive: false,
    });
    scrollContainer.addEventListener("touchmove", handleTouchMove, {
      passive: false,
    });
    scrollContainer.addEventListener("touchend", handleTouchEnd);

    return () => {
      scrollContainer.removeEventListener("wheel", handleWheel);
      scrollContainer.removeEventListener("touchstart", handleTouchStart);
      scrollContainer.removeEventListener("touchmove", handleTouchMove);
      scrollContainer.removeEventListener("touchend", handleTouchEnd);
    };
  }, []);

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
      {/* h1 positioned at bottom */}
      <nav className="fixed bottom-0 left-0 z-10 flex w-full items-center justify-between border-t-[1px] border-t-neutral-300 bg-[#82aecc] px-4 py-1">
        <h1 className="text-lg tracking-tight">horizon at sea</h1>
        <p className="hidden text-sm text-neutral-800 sm:block">
          a chronology of {IMAGES.length} horizons at sea, sourced from{" "}
          <Link
            href="https://unsplash.com"
            target="_blank"
            className="underline"
          >
            Unsplash
          </Link>
        </p>
        <Link
          href="https://www.yufengzhao.com/projects/desk-setup"
          target="_blank"
          className="text-sm text-neutral-800 underline"
        >
          about
        </Link>
      </nav>

      {/* Main content */}
      <div className="flex min-h-screen flex-col items-center justify-center">
        <div className="flex w-full justify-start">
          <div
            className="flex min-h-screen items-center overflow-x-auto pb-4"
            ref={scrollContainerRef}
          >
            {IMAGES.map((image, index) => (
              <div className="relative" key={image.id}>
                <DeskSetupImage imageWithUser={image} />
                {/* <div className="absolute top-0 right-0 bottom-0 left-0 flex translate-y-[400px] items-center justify-center">
                  <span className="text-sm text-white/40 transition-all duration-300 select-none hover:text-white">
                    {new Date(image.created_at).toLocaleDateString("en-US", {
                      year: "numeric",
                      month: "long",
                      day: "numeric",
                    })}
                  </span>
                </div> */}
              </div>
            ))}
          </div>
        </div>
      </div>
    </main>
  );
}
