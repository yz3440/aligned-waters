import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

import { type ImageWithUser } from "@/data/imageWithUser";
import Image from "next/image";
import Link from "next/link";
import { useMemo } from "react";

interface DeskSetupImageDialogProps {
  imageWithUser: ImageWithUser;
  children: React.ReactNode;
}

export function DeskSetupImageDialog({
  children,
  imageWithUser,
}: DeskSetupImageDialogProps) {
  // Generate a random rotation angle for this component instance
  const randomRotation = useMemo(() => {
    return Math.random() * 360; // Random angle between 0 and 360 degrees
  }, []);

  return (
    <Dialog>
      <DialogTrigger asChild>{children}</DialogTrigger>
      <DialogContent
        showCloseButton={false}
        className="overflow-hidden p-8 pb-6"
      >
        <DialogTitle className="sr-only">
          {imageWithUser.alt_description}
        </DialogTitle>
        <div
          className="absolute inset-0 -z-10"
          style={{
            backgroundImage: "url(/231-subtle-white-paper.webp)",
            backgroundSize: "cover",
            backgroundPosition: "center",
            backgroundRepeat: "no-repeat",
            transform: `rotate(${randomRotation}deg) scale(2)`,
            transformOrigin: "center",
          }}
        />
        <Link href={imageWithUser.html_link} target="_blank">
          <Image
            src={imageWithUser.regular_image_src}
            alt={
              imageWithUser.description ?? imageWithUser.alt_description ?? ""
            }
            className="h-full w-full object-cover transition-opacity duration-300 select-none"
            style={{
              // 4 thin borders: top (light), right (medium), bottom (dark), left (medium-light)
              borderTop: "2px solid #ccc", // top: white highlight
              borderRight: "2px solid #e5e7eb", // right: light gray
              borderBottom: "2px solid #acacac", // bottom: dark gray
              borderLeft: "2px solid #d1d5db", // left: medium gray
            }}
            loading="lazy"
            height={500}
            width={625}
            unoptimized
          />
        </Link>

        <div className="mt-0">
          <p className="text-sm italic">
            &quot;{imageWithUser.description ?? imageWithUser.alt_description}
            &quot;
          </p>

          <p className="text-muted-foreground font-cursive text-right text-sm">
            <Link
              href={imageWithUser.user.html_link}
              target="_blank"
              className="underline"
            >
              {imageWithUser.user.name}
            </Link>
          </p>

          <p className="text-muted-foreground text-right text-xs">
            {new Date(imageWithUser.created_at).toLocaleDateString("en-US", {
              year: "numeric",
              month: "long",
              day: "numeric",
            })}
          </p>
        </div>
      </DialogContent>
    </Dialog>
  );
}
