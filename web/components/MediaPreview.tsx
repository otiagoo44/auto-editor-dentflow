"use client";
import { useEffect, useState } from "react";
export function MediaPreview({
  identity,
  url,
  className,
}: {
  identity: string;
  url: string;
  className?: string;
}) {
  // Polling renews download tickets. Do not reset playback each time the URL changes.
  const [source, setSource] = useState(url);
  useEffect(() => {
    setSource(url);
  }, [identity]);
  return (
    <video
      className={className}
      src={source}
      controls
      playsInline
      preload="metadata"
      onError={() => {
        if (source !== url) setSource(url);
      }}
    />
  );
}
