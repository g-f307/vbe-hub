'use client'

import { useId } from 'react'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { cn } from '@/lib/utils'

export type FilterOption = { value: string; label: string }

export function FilterSelect({
  label,
  value,
  onChange,
  options,
  className,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  options: FilterOption[]
  className?: string
}) {
  const id = useId()
  return (
    <div className={cn('flex min-w-0 flex-col gap-1', className)}>
      <Label htmlFor={id} className="text-xs font-medium text-ardosia">
        {label}
      </Label>
      <Select items={options} value={value} onValueChange={(v) => v != null && onChange(String(v))}>
        <SelectTrigger id={id} className="h-9 w-full bg-mineral">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {options.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}
