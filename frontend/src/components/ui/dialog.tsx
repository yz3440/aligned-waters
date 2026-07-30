import * as React from "react";
import { useCallback, useEffect, useRef, useState } from "react";

import { cn } from "@/lib/utils";

/** Keep in sync with the dialog transition duration in globals.css. */
const EXIT_MS = 200;

interface DialogProps {
  /** The element that opens the dialog. Rendered inline, wrapped in a button. */
  trigger: React.ReactNode;
  /** Accessible name for the dialog. */
  label: string;
  className?: string;
  children: React.ReactNode;
}

/**
 * Modal dialog on the native <dialog> element: showModal() provides the top
 * layer, focus trapping, ESC-to-close and focus restoration. We add body
 * scroll lock, click-outside dismissal, and a delayed unmount so the exit
 * transition in globals.css can play.
 */
function Dialog({ trigger, label, className, children }: DialogProps) {
  const ref = useRef<HTMLDialogElement>(null);
  // Mounted only while in use, so thousands of these cost nothing at rest.
  const [isMounted, setIsMounted] = useState(false);
  const unmountTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const open = useCallback(() => {
    if (unmountTimer.current) {
      clearTimeout(unmountTimer.current);
      unmountTimer.current = null;
    }
    // Still mounted mid-exit: reopen it directly, since the mount effect below
    // won't re-run.
    if (isMounted) ref.current?.showModal();
    else setIsMounted(true);
  }, [isMounted]);

  // showModal() must run once the <dialog> is in the DOM.
  useEffect(() => {
    if (!isMounted) return;
    ref.current?.showModal();

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [isMounted]);

  useEffect(() => {
    return () => {
      if (unmountTimer.current) clearTimeout(unmountTimer.current);
    };
  }, []);

  // Fires for every close path, ours and ESC alike.
  const onNativeClose = useCallback(() => {
    unmountTimer.current = setTimeout(() => setIsMounted(false), EXIT_MS + 50);
  }, []);

  // A click reaches the <dialog> itself only when it lands on the backdrop —
  // the content sits in a child element.
  const onBackdropClick = useCallback(
    (event: React.MouseEvent<HTMLDialogElement>) => {
      if (event.target === ref.current) ref.current?.close();
    },
    [],
  );

  return (
    <>
      <button
        type="button"
        data-slot="dialog-trigger"
        className="block w-full cursor-pointer"
        onClick={open}
      >
        {trigger}
      </button>

      {isMounted && (
        <dialog
          ref={ref}
          data-slot="dialog"
          aria-label={label}
          className="m-auto bg-transparent p-0"
          onClick={onBackdropClick}
          onClose={onNativeClose}
        >
          <div
            data-slot="dialog-content"
            className={cn(
              // `isolate` creates a stacking context so children with negative
              // z-index (e.g. a background texture) paint above this element's
              // own background instead of escaping behind the dialog.
              "bg-background isolate grid w-full max-w-[calc(100vw-2rem)] gap-4 border p-6 shadow-lg sm:max-w-lg",
              className,
            )}
          >
            {children}
          </div>
        </dialog>
      )}
    </>
  );
}

export { Dialog };
