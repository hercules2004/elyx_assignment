"use client"

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { AlertCircle } from "lucide-react"

interface SwapModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  originalActivity: { id: string; name: string } | null
  backupActivity: { id: string; name: string } | null
  onConfirmSwap: () => void
}

export function SwapModal({ open, onOpenChange, originalActivity, backupActivity, onConfirmSwap }: SwapModalProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <div className="flex items-center gap-2 mb-2">
            <div className="p-2 rounded-lg bg-primary/10">
              <AlertCircle className="h-5 w-5 text-primary" />
            </div>
            <DialogTitle>Plan B Available</DialogTitle>
          </div>
          <DialogDescription className="text-base leading-relaxed">
            Would you like to swap to an alternative activity?
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3 py-4">
          <div className="p-3 rounded-lg bg-secondary">
            <p className="text-xs text-muted-foreground mb-1">Current</p>
            <p className="font-semibold">{originalActivity?.name}</p>
          </div>

          <div className="flex justify-center">
            <div className="text-muted-foreground">→</div>
          </div>

          <div className="p-3 rounded-lg bg-primary/10 border-2 border-primary">
            <p className="text-xs text-primary mb-1">Alternative</p>
            <p className="font-semibold text-primary">{backupActivity?.name}</p>
          </div>
        </div>

        <DialogFooter className="flex-col sm:flex-row gap-2">
          <Button variant="outline" onClick={() => onOpenChange(false)} className="w-full sm:w-auto">
            Keep Original
          </Button>
          <Button
            onClick={() => {
              onConfirmSwap()
              onOpenChange(false)
            }}
            className="w-full sm:w-auto"
          >
            Switch to Plan B
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
