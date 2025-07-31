"use client";

import Link from "next/link";

import { IMAGES_WITH_USERS } from "@/data/imageWithUser";
import { env } from "@/env";
import DeskSetupImage from "./_components/DeskSetupImage";

import { getHue } from "@/lib/colorUtils";

export default function Home() {
  const IMAGES = [...IMAGES_WITH_USERS].sort((a, b) => {
    const aHue = getHue(a.color);
    const bHue = getHue(b.color);
    return bHue - aHue;
  });

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
      <nav className="fixed bottom-0 left-0 z-10 flex w-full items-center justify-between border-t-[1px] border-t-neutral-300 bg-white/60 px-4 py-1">
        <h1 className="text-lg tracking-tight">horizon at sea</h1>
        <p className="hidden text-sm text-neutral-500 sm:block">
          all {IMAGES.length} horizon at sea shots sourced from{" "}
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
          className="text-sm text-neutral-500 underline"
        >
          about
        </Link>
      </nav>

      {/* Main content */}
      <div className="flex min-h-screen flex-col items-center justify-center">
        <div className="flex w-full justify-start">
          <div className="flex min-h-screen items-center overflow-x-auto pb-4">
            {IMAGES.map((image, index) => (
              <DeskSetupImage key={image.id} imageWithUser={image} />
            ))}
          </div>
        </div>
      </div>
    </main>
  );
}
