'use client';

import clsx from 'clsx';
import { createContext, useContext, useMemo, useState } from 'react';

export type Tab = {
  key: string;
  label: string;
  content: React.ReactNode;
};

type TabsContextValue = {
  activeKey: string;
  setActiveKey: (key: string) => void;
};

const TabsContext = createContext<TabsContextValue | null>(null);

export function useTabs() {
  const ctx = useContext(TabsContext);
  if (!ctx) {
    throw new Error('useTabs must be used within Tabs');
  }
  return ctx;
}

export function Tabs({
  tabs,
  initialKey,
}: {
  tabs: Tab[];
  initialKey?: string;
}) {
  const [activeKey, setActiveKey] = useState(initialKey ?? tabs[0]?.key ?? '');
  const value = useMemo(() => ({ activeKey, setActiveKey }), [activeKey]);

  const activeTab = tabs.find((tab) => tab.key === activeKey) ?? tabs[0];

  return (
    <TabsContext.Provider value={value}>
      <div>
        <div className="flex flex-wrap gap-2">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              type="button"
              onClick={() => setActiveKey(tab.key)}
              className={clsx(
                'rounded-lg px-4 py-2 text-sm font-medium transition-colors',
                tab.key === activeKey
                  ? 'bg-indigo-600 text-white shadow'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200',
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <div className="mt-4">
          {activeTab ? <div className="space-y-4 text-sm text-slate-700">{activeTab.content}</div> : null}
        </div>
      </div>
    </TabsContext.Provider>
  );
}
