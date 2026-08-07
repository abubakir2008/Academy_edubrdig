"use client";

import Script from "next/script";
import { useEffect, useId, useRef, useState } from "react";

import { useAuth } from "@/lib/auth";

const CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;

type CredentialResponse = { credential: string };

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: {
            client_id: string;
            callback: (response: CredentialResponse) => void;
          }) => void;
          renderButton: (parent: HTMLElement, options: Record<string, unknown>) => void;
        };
      };
    };
  }
}

/**
 * Renders nothing if NEXT_PUBLIC_GOOGLE_CLIENT_ID isn't set at build time —
 * see Dockerfile/docker-compose.yml (build.args) for why it has to be there,
 * not just in the container's runtime environment.
 */
export function GoogleSignInButton({ onError }: { onError?: (message: string) => void }) {
  const { loginWithGoogle, refreshUser } = useAuth();
  const [ready, setReady] = useState(false);
  const containerId = useId();
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ready || !CLIENT_ID || !window.google || !containerRef.current) return;
    window.google.accounts.id.initialize({
      client_id: CLIENT_ID,
      callback: (response) => {
        loginWithGoogle(response.credential)
          .then((user) => {
            window.location.href = user.role === "tutor" ? "/dashboard" : "/dashboard";
          })
          .catch((e) => {
            onError?.(e instanceof Error ? e.message : "Не удалось войти через Google");
            void refreshUser();
          });
      },
    });
    window.google.accounts.id.renderButton(containerRef.current, {
      theme: "outline",
      size: "large",
      width: 320,
      locale: "ru",
    });
  }, [ready, loginWithGoogle, refreshUser, onError]);

  if (!CLIENT_ID) return null;

  return (
    <>
      <Script src="https://accounts.google.com/gsi/client" strategy="afterInteractive" onReady={() => setReady(true)} />
      <div className="flex justify-center" id={containerId} ref={containerRef} />
    </>
  );
}
