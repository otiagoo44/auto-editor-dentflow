import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "DentFlow Studio",
  description:
    "Tu grabación, un Reel claro. Edición privada con tu motor local.",
};
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
