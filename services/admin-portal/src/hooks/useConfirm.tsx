'use client';

import { useState, useCallback } from 'react';
import Dialog from '@/components/primitives/Dialog';

interface ConfirmOptions {
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
}

export function useConfirm() {
  const [isOpen, setIsOpen] = useState(false);
  const [options, setOptions] = useState<ConfirmOptions | null>(null);
  const [resolveRef, setResolveRef] = useState<((value: boolean) => void) | null>(null);

  const confirm = useCallback((options: ConfirmOptions): Promise<boolean> => {
    setOptions(options);
    setIsOpen(true);
    return new Promise((resolve) => {
      setResolveRef(() => resolve);
    });
  }, []);

  const handleConfirm = useCallback(() => {
    if (resolveRef) {
      resolveRef(true);
    }
    setIsOpen(false);
  }, [resolveRef]);

  const handleCancel = useCallback(() => {
    if (resolveRef) {
      resolveRef(false);
    }
    setIsOpen(false);
  }, [resolveRef]);

  return {
    confirm,
    ConfirmDialog: options ? (
      <Dialog
        open={isOpen}
        onClose={() => setIsOpen(false)}
        title={options.title}
        description={options.message}
        onConfirm={handleConfirm}
        onCancel={handleCancel}
        confirmText={options.confirmText || 'Confirm'}
        cancelText={options.cancelText || 'Cancel'}
      />
    ) : null,
  };
}