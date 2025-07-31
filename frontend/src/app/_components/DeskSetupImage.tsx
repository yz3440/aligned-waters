"use client";

import Image from "next/image";
import { motion } from "motion/react";
import { useState, useMemo } from "react";
import Link from "next/link";

import { type ImageWithUser } from "@/data/imageWithUser";
import { DeskSetupImageDialog } from "./DeskSetupImageDialog";
import { cn } from "@/lib/utils";

interface DeskSetupImageProps {
  imageWithUser: ImageWithUser;
  withFrame?: boolean;
}

export default function DeskSetupImage({
  imageWithUser,
  withFrame = false,
}: DeskSetupImageProps) {
  const [isLoading, setIsLoading] = useState(true);

  // Generate a random rotation angle for this component instance
  const randomRotation = useMemo(() => {
    return Math.random() * 360; // Random angle between 0 and 360 degrees
  }, []);

  return (
    <div
      className={cn("relative ml-4", withFrame ? "p-8 shadow-sm md:p-12" : "")}
    >
      {/* Rotating background layer */}
      {withFrame && (
        <div
          className="absolute inset-0"
          style={{
            backgroundImage: "url(/231-subtle-white-paper.webp)",
            backgroundSize: "cover",
            backgroundPosition: "center",
            backgroundRepeat: "no-repeat",
            transform: `rotate(${randomRotation}deg) scale(2)`,
            transformOrigin: "center",
          }}
        />
      )}

      {/* Content layer */}
      <motion.div
        className="relative w-48 flex-shrink-0 md:w-64"
        style={
          withFrame
            ? {
                // 4 thin borders: top (light), right (medium), bottom (dark), left (medium-light)
                borderTop: "2px solid #ccc", // top: white highlight
                borderRight: "2px solid #e5e7eb", // right: light gray
                borderBottom: "2px solid #acacac", // bottom: dark gray
                borderLeft: "2px solid #d1d5db", // left: medium gray
              }
            : {}
        }
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.3 }}
      >
        {/* Pulsing loading animation */}
        {isLoading && (
          <motion.div
            className="absolute inset-0 bg-gray-200"
            animate={{
              opacity: [0.5, 1, 0.5],
            }}
            transition={{
              duration: 1.5,
              repeat: Infinity,
              ease: "easeInOut",
            }}
          />
        )}

        <DeskSetupImageDialog imageWithUser={imageWithUser}>
          <Image
            src={imageWithUser.regular_image_src}
            alt={
              imageWithUser.description ?? imageWithUser.alt_description ?? ""
            }
            className={cn(
              "h-full w-full object-cover transition-opacity duration-300 select-none",
              isLoading ? "opacity-0" : "opacity-100",
              "cursor-pointer",
            )}
            style={{
              transform: `translateY(${(0.5 - imageWithUser.horizon_y) * 100}%)`,
            }}
            loading="lazy"
            unoptimized
            width={1080}
            height={1080 / (imageWithUser.width / imageWithUser.height)}
            onLoad={() => setIsLoading(false)}
            onError={() => setIsLoading(false)}
          />
        </DeskSetupImageDialog>
      </motion.div>

      {/* <div className="absolute right-0 bottom-0 px-2 py-1">
        <Link
          href={imageWithUser.user.html_link}
          target="_blank"
          className="font-cursive text-xs transition-colors duration-300 hover:underline"
          style={{
            filter: `invert(1) brightness(1.5)`,
            color: "inherit",
          }}
        >
          <p className="">{imageWithUser.user.name}</p>
        </Link>
      </div> */}
    </div>
  );
}
