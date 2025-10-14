'use client';

import { Dialog, Transition } from '@headlessui/react';
import { Fragment } from 'react';

export type DrawerProps = {
  title: string;
  isOpen: boolean;
  onClose: () => void;
  children: React.ReactNode;
  side?: 'left' | 'right';
};

export default function Drawer({ title, isOpen, onClose, side = 'right', children }: DrawerProps) {
  const sideClasses = side === 'right' ? 'right-0 translate-x-full' : 'left-0 -translate-x-full';

  return (
    <Transition show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-200"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-150"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black/30" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-hidden">
          <div
            className="absolute inset-y-0 flex max-w-full"
            style={{ [side]: 0 }}
          >
            <Transition.Child
              as={Fragment}
              enter="transform transition ease-out duration-200"
              enterFrom={sideClasses}
              enterTo="translate-x-0"
              leave="transform transition ease-in duration-150"
              leaveFrom="translate-x-0"
              leaveTo={sideClasses}
            >
              <Dialog.Panel className="pointer-events-auto w-screen max-w-md bg-white shadow-xl">
                <div className="flex h-full flex-col">
                  <div className="border-b border-slate-200 px-6 py-4">
                    <Dialog.Title className="text-base font-semibold text-slate-900">
                      {title}
                    </Dialog.Title>
                  </div>
                  <div className="flex-1 overflow-y-auto px-6 py-4 text-sm text-slate-600">
                    {children}
                  </div>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  );
}
