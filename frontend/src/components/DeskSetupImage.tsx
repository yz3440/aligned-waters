import { useState, useMemo } from "react";

import { type ImageWithUser } from "@/types";
import { DeskSetupImageDialog } from "./DeskSetupImageDialog";
import { cn } from "@/lib/utils";

interface DeskSetupImageProps {
  imageWithUser: ImageWithUser;
}

export default function DeskSetupImage({ imageWithUser }: DeskSetupImageProps) {
  const [isLoading, setIsLoading] = useState(true);

  // The strip renders at 192–256 CSS px, so request a small variant; the
  // dialog keeps the original w=1080 URL.
  const stripImageSrc = useMemo(() => {
    const url = new URL(imageWithUser.regular_image_src);
    url.searchParams.set("w", "400");
    return url.toString();
  }, [imageWithUser.regular_image_src]);

  return (
    <div className="relative ml-0">
      <div className="animate-fade-in relative w-48 flex-shrink-0 md:w-64">
        {/* Pulsing loading animation */}
        {isLoading && (
          <div className="absolute inset-0 animate-pulse bg-gray-200" />
        )}

        <DeskSetupImageDialog imageWithUser={imageWithUser}>
          <img
            src={stripImageSrc}
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
            width={1080}
            height={1080 / (imageWithUser.width / imageWithUser.height)}
            onLoad={() => setIsLoading(false)}
            onError={() => setIsLoading(false)}
          />
        </DeskSetupImageDialog>
      </div>
    </div>
  );
}
