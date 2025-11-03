'use client';

import { Dialog, Transition } from '@headlessui/react';
import clsx from 'clsx';
import { useRouter } from 'next/navigation';
import type { KeyboardEvent as ReactKeyboardEvent } from 'react';
import {
  Fragment,
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { NAV_ITEMS } from '@/components/layout/Sidebar';
import { getQuickCreateLinks } from '@/lib/guards';

type CommandSection = 'Navigation' | 'Quick actions';

type Command = {
  id: string;
  label: string;
  hint?: string;
  section: CommandSection;
  action: () => void;
  keywords: string;
};

type CommandPaletteContextValue = {
  open: () => void;
  openQuickActions: () => void;
  close: () => void;
  toggle: () => void;
};

const CommandPaletteContext = createContext<CommandPaletteContextValue | undefined>(undefined);

export function CommandPaletteProvider({ children }: { children: React.ReactNode }) {
  const [isOpen, setOpen] = useState(false);
  const [focusSection, setFocusSection] = useState<CommandSection | null>(null);

  const open = useCallback(() => {
    setFocusSection(null);
    setOpen(true);
  }, []);
  const openQuickActions = useCallback(() => {
    setFocusSection('Quick actions');
    setOpen(true);
  }, []);
  const close = useCallback(() => {
    setOpen(false);
    setFocusSection(null);
  }, []);
  const toggle = useCallback(() => {
    setOpen((current) => {
      if (current) {
        setFocusSection(null);
      }
      return !current;
    });
  }, []);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        toggle();
        return;
      }
      if (event.key === 'Escape') {
        setOpen(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [toggle]);

  return (
    <CommandPaletteContext.Provider value={{ open, openQuickActions, close, toggle }}>
      {children}
      <CommandPalette isOpen={isOpen} onClose={close} focusSection={focusSection} />
    </CommandPaletteContext.Provider>
  );
}

export function useCommandPalette() {
  const ctx = useContext(CommandPaletteContext);
  if (!ctx) {
    throw new Error('useCommandPalette must be used within CommandPaletteProvider');
  }
  return ctx;
}

function CommandPalette({
  isOpen,
  onClose,
  focusSection,
}: {
  isOpen: boolean;
  onClose: () => void;
  focusSection: CommandSection | null;
}) {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const quickCreates = useMemo(() => getQuickCreateLinks(), []);

  const commands = useMemo<Command[]>(() => {
    const navigationCommands: Command[] = [
      ...NAV_ITEMS.map((item) => ({
        id: `nav-${item.href}`,
        label: item.label,
        hint: item.href,
        section: 'Navigation',
        keywords: `${item.label.toLowerCase()} ${item.href.toLowerCase()}`,
        action: () => {
          router.push(item.href);
          onClose();
        },
      })),
      {
        id: 'nav-profile',
        label: 'Profile',
        hint: '/profile',
        section: 'Navigation',
        keywords: 'profile account settings user',
        action: () => {
          router.push('/profile');
          onClose();
        },
      },
    ];

    const quickCommands: Command[] = quickCreates.map((link, index) => ({
      id: `quick-${index}`,
      label: link.label,
      hint: 'Quick action',
      section: 'Quick actions',
      keywords: `${link.label.toLowerCase()} ${link.pathname.toLowerCase()} quick create`,
      action: () => {
        const queryString =
          link.query && Object.keys(link.query).length > 0
            ? new URLSearchParams(link.query).toString()
            : '';
        router.push(queryString ? `${link.pathname}?${queryString}` : link.pathname);
        onClose();
      },
    }));

    return [...navigationCommands, ...quickCommands];
  }, [onClose, quickCreates, router]);

  const [query, setQuery] = useState('');
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    if (isOpen) {
      setQuery('');
      requestAnimationFrame(() => {
        inputRef.current?.focus();
      });
    }
  }, [isOpen]);

  const filteredCommands = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term) {
      return commands;
    }
    return commands.filter((command) => command.keywords.includes(term));
  }, [commands, query]);

  useEffect(() => {
    if (!isOpen) return;
    if (focusSection) {
      const firstIndex = filteredCommands.findIndex((command) => command.section === focusSection);
      setActiveIndex(firstIndex >= 0 ? firstIndex : 0);
      return;
    }
    setActiveIndex(0);
  }, [isOpen, focusSection, filteredCommands]);

  const sections = useMemo(() => {
    const grouped = new Map<CommandSection, Command[]>();
    for (const command of filteredCommands) {
      const bucket = grouped.get(command.section);
      if (bucket) {
        bucket.push(command);
      } else {
        grouped.set(command.section, [command]);
      }
    }
    return Array.from(grouped.entries());
  }, [filteredCommands]);

  const handleInputKeyDown = (event: ReactKeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      if (filteredCommands.length === 0) return;
      setActiveIndex((current) => Math.min(current + 1, filteredCommands.length - 1));
      return;
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault();
      if (filteredCommands.length === 0) return;
      setActiveIndex((current) => Math.max(current - 1, 0));
      return;
    }
    if (event.key === 'Enter') {
      event.preventDefault();
      const command = filteredCommands[activeIndex];
      if (command) {
        command.action();
      }
    }
  };

  const handleSelect = (command: Command) => {
    command.action();
  };

  return (
    <Transition appear show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-150"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-100"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-start justify-center px-4 pb-12 pt-24 sm:pt-32">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-150"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-100"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="w-full max-w-xl overflow-hidden rounded-2xl bg-white shadow-2xl ring-1 ring-black/10">
                <div className="flex items-center gap-3 border-b border-slate-200 px-4 py-3">
                  <input
                    ref={inputRef}
                    value={query}
                    onChange={(event) => {
                      setQuery(event.target.value);
                      setActiveIndex(0);
                    }}
                    onKeyDown={handleInputKeyDown}
                    placeholder="Search pages and actions..."
                    className="h-10 w-full border-none bg-transparent text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none"
                    aria-label="Search"
                  />
                  <span className="rounded bg-slate-100 px-2 py-1 text-[11px] font-medium text-slate-500">ESC</span>
                </div>

                <div className="max-h-80 overflow-y-auto p-2">
                  {filteredCommands.length === 0 ? (
                    <p className="px-4 py-6 text-center text-sm text-slate-500">No matches found.</p>
                  ) : (
                    sections.map(([section, items]) => (
                      <div key={section} className="mb-3">
                        <p className="px-3 pb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
                          {section}
                        </p>
                        <ul className="space-y-1">
                          {items.map((item) => {
                            const index = filteredCommands.indexOf(item);
                            const isActive = index === activeIndex;
                            return (
                              <li key={item.id}>
                                <button
                                  type="button"
                                  onClick={() => handleSelect(item)}
                                  onMouseEnter={() => setActiveIndex(index)}
                                  className={clsx(
                                    'flex w-full items-center justify-between rounded-xl px-3 py-2 text-left text-sm transition-colors',
                                    isActive
                                      ? 'bg-indigo-50 text-indigo-600'
                                      : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900',
                                  )}
                                >
                                  <span>{item.label}</span>
                                  {item.hint ? (
                                    <span className="text-xs font-medium text-slate-400">{item.hint}</span>
                                  ) : null}
                                </button>
                              </li>
                            );
                          })}
                        </ul>
                      </div>
                    ))
                  )}
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  );
}
