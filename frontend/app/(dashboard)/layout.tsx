import { Navigation } from '@/components/layout/navigation';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex">
      <Navigation />
      <main className="flex-1 ml-64 p-8">
        {children}
      </main>
    </div>
  );
}
