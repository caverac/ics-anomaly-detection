import { cva, type VariantProps } from 'class-variance-authority'
import { type HTMLAttributes } from 'react'

import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
  {
    variants: {
      variant: {
        default: 'border-transparent bg-primary text-primary-foreground',
        secondary: 'border-transparent bg-secondary text-secondary-foreground',
        outline: 'border-border text-foreground',
        destructive: 'border-transparent bg-destructive text-destructive-foreground',
        warning: 'border-transparent bg-warning text-warning-foreground',
        // Severity variants
        low: 'border-transparent bg-severity-low/20 text-severity-low',
        medium: 'border-transparent bg-severity-medium/20 text-severity-medium',
        high: 'border-transparent bg-severity-high/20 text-severity-high',
        critical: 'border-transparent bg-severity-critical/20 text-severity-critical',
        // Priority variants
        p1: 'border-transparent bg-priority-p1/20 text-priority-p1',
        p2: 'border-transparent bg-priority-p2/20 text-priority-p2',
        p3: 'border-transparent bg-priority-p3/20 text-priority-p3',
        p4: 'border-transparent bg-priority-p4/20 text-priority-p4',
        // Status variants
        open: 'border-transparent bg-destructive/20 text-destructive',
        acknowledged: 'border-transparent bg-warning/20 text-warning',
        resolved: 'border-transparent bg-primary/20 text-primary',
        active: 'border-transparent bg-destructive/20 text-destructive'
      }
    },
    defaultVariants: {
      variant: 'default'
    }
  }
)

export interface BadgeProps
  extends HTMLAttributes<HTMLDivElement>, VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />
}
