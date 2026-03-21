'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  BookOpen,
  FolderKanban,
  FileText,
  Search,
  Activity,
  Settings,
  BarChart3,
} from 'lucide-react';

const navItems = [
  { href: '/', label: 'Dashboard', icon: BookOpen },
  { href: '/projects', label: 'Projects', icon: FolderKanban },
  { href: '/search', label: 'Search', icon: Search },
  { href: '/jobs', label: 'Jobs', icon: Activity },
  { href: '/analytics', label: 'Analytics', icon: BarChart3 },
  { href: '/settings', label: 'Settings', icon: Settings },
];

export function Navigation() {
  const pathname = usePathname();

  return (
    <nav className="fixed left-0 top-0 h-full w-64 bg-card border-r p-4">
      {/* Logo */}
      <Link href="/" className="flex items-center gap-2 mb-8 px-2">
        <BookOpen className="h-8 w-8 text-primary" />
        <span className="text-xl font-bold">Aegis</span>
      </Link>

      {/* Nav Items */}
      <ul className="space-y-1">
        {navItems.map((item) => {
          const isActive = pathname === item.href ||
            (item.href !== '/' && pathname.startsWith(item.href));
          const Icon = item.icon;

          return (
            <li key={item.href}>
              <Link
                href={item.href}
                className={`
                  flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium
                  transition-colors
                  ${isActive
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                  }
                `}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </Link>
            </li>
          );
        })}
      </ul>

      {/* Footer */}
      <div className="absolute bottom-4 left-4 right-4">
        <div className="text-xs text-muted-foreground text-center">
          Aegis v0.1.0
        </div>
      </div>
    </nav>
  );
}
