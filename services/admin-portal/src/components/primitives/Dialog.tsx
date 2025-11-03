'use client';

import { Fragment } from 'react';
import { Dialog as HeadlessUI, Transition } from '@headlessui/react';
import Button from '@/components/primitives/Button';

interface DialogProps {
  readonly open: boolean;
  readonly onClose: () => void;
  readonly title: string;
  readonly description: string;
  readonly onConfirm: () => void;
  readonly onCancel: () => void;
  readonly confirmText?: string;
  readonly cancelText?: string;
}

export default function ConfirmationDialog({
  open,
  onClose,
  title,
  description,
  onConfirm,
  onCancel,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
}: DialogProps) {
  return (
    <Transition appear show={open} as={Fragment}>
      <HeadlessUI className="relative z-50" onClose={onClose}>
        <Transition
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black bg-opacity-25" />
        </Transition>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4 text-center">
            <Transition
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <div className="w-full max-w-md transform overflow-hidden rounded-lg bg-white p-6 text-left align-middle shadow-xl transition-all">
                <h3 className="text-lg font-semibold text-slate-900">
                  {title}
                </h3>
                <div className="mt-2">
                  <p className="text-sm text-slate-500">{description}</p>
                </div>

                <div className="mt-6 flex justify-end space-x-3">
                        <Button onClick={onCancel} className="bg-gray-100 text-gray-900 hover:bg-gray-200">
                    {cancelText}
                  </Button>
                        <Button onClick={onConfirm} className="bg-blue-600 text-white hover:bg-blue-700">
                    {confirmText}
                  </Button>
                </div>
              </div>
            </Transition>
          </div>
        </div>
      </HeadlessUI>
    </Transition>
  );
}