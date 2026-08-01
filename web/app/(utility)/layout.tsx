import UtilitySidebar from "@/components/sidebar/UtilitySidebar";
import { CapabilityAccessProvider } from "@/components/access/CapabilityAccessContext";
import CapabilityGate from "@/components/access/CapabilityGate";

export default function UtilityLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <CapabilityAccessProvider>
      <div className="flex h-screen overflow-hidden">
        <UtilitySidebar />
        <main className="beach-surface flex-1 overflow-hidden">
          <CapabilityGate>{children}</CapabilityGate>
        </main>
      </div>
    </CapabilityAccessProvider>
  );
}
