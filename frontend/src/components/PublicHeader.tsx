import { Flame } from 'lucide-react'

export function PublicHeader() {
  return (
    <header className="sticky top-0 z-10 border-b border-gray-200 bg-white/90 backdrop-blur px-4 py-4">
      <div className="mx-auto flex max-w-3xl items-center gap-2">
        <Flame className="h-6 w-6 text-flame" />
        <span className="text-lg font-bold tracking-tight text-gray-900">Fire Conference</span>
      </div>
    </header>
  )
}
