// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/admin-portal/components/primitives/Modal.tsx
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/admin-portal/components/primitives/Modal.tsx.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

'use client';

import { Dialog, Transition } from '@headlessui/react';
import { Fragment } from 'react';
import Button from './Button';

type ModalProps = {
  title: string;
  isOpen: boolean;
  onClose: () => void;
  children: React.ReactNode;
  primaryActionLabel?: string;
  onPrimaryAction?: () => void;
  isPrimaryDisabled?: boolean;
};

export default function Modal({
  title,
  isOpen,
  onClose,
  children,
  primaryActionLabel,
  onPrimaryAction,
  isPrimaryDisabled,
}: ModalProps) {
  return (
    <Transition show={isOpen} as={Fragment}>
      <Dialog
        as="div"
        className="relative z-50"
        onClose={onClose}
      >
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-200"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-150"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black/40" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-200"
              enterFrom="opacity-0 translate-y-2"
              enterTo="opacity-100 translate-y-0"
              leave="ease-in duration-150"
              leaveFrom="opacity-100 translate-y-0"
              leaveTo="opacity-0 translate-y-2"
            >
              <Dialog.Panel className="w-full max-w-2xl rounded-2xl bg-white p-6 shadow-xl">
                <Dialog.Title className="text-lg font-semibold text-slate-900">{title}</Dialog.Title>
                <div className="mt-4 text-sm text-slate-600">{children}</div>
                <div className="mt-6 flex justify-end gap-2">
                  <Button variant="ghost" onClick={onClose} type="button">
                    Cancel
                  </Button>
                  {primaryActionLabel ? (
                    <Button
                      type="button"
                      onClick={onPrimaryAction}
                      disabled={isPrimaryDisabled}
                    >
                      {primaryActionLabel}
                    </Button>
                  ) : null}
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  );
}
