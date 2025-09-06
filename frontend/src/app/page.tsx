import { Suspense } from "react";

import HomeClient from "./page.client";

export default function Home() {
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
      <Suspense fallback={<div>Loading...</div>}>
        <HomeClient />
      </Suspense>
    </main>
  );
}
