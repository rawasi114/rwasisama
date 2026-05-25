import * as React from 'react';
import { cn } from '@/lib/utils';

export const Label = ({ className, ...props }: React.LabelHTMLAttributes<HTMLLabelElement>) => (
  <label className={cn('mb-1.5 block text-sm font-medium text-navy', className)} {...props} />
);
