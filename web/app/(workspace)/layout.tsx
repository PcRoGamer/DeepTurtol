// WorkspaceSidebar is the active workspace controller. It supplies session
// state/actions to SidebarShell; it is not an alternate visual sidebar.
import WorkspaceSidebar from "@/components/sidebar/WorkspaceSidebar";
import PebbleConversationSwitcher from "@/components/PebbleConversationSwitcher";
import { CapabilityAccessProvider } from "@/components/access/CapabilityAccessContext";
import CapabilityGate from "@/components/access/CapabilityGate";
import { UnifiedChatProvider } from "@/context/UnifiedChatContext";

export default function WorkspaceLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <CapabilityAccessProvider>
      <UnifiedChatProvider>
        <div className="flex h-screen overflow-hidden">
          <WorkspaceSidebar />
          <div className="flex flex-1 flex-col overflow-hidden bg-gradient-to-br from-[#FDF8EE] to-[#E6D5B8] text-[var(--foreground)]">
            <PebbleConversationSwitcher />
            <main className="flex-1 overflow-hidden">
              <CapabilityGate>{children}</CapabilityGate>
            </main>
          </div>
        </div>
      </UnifiedChatProvider>
    </CapabilityAccessProvider>
  );
}

