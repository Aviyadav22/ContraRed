import { useState } from 'react'
import {
  DndContext,
  closestCenter,
  PointerSensor,
  KeyboardSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import {
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
  arrayMove,
  sortableKeyboardCoordinates,
} from '@dnd-kit/sortable'

interface DragDropProps {
  items: string[]
  correctOrder: string[]
  onComplete: (userOrder: string[]) => void
}

function SortableItem({
  id,
  status,
}: {
  id: string
  status: 'idle' | 'correct' | 'wrong'
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id })

  const style: React.CSSProperties = {
    transform: transform
      ? `translate3d(${transform.x}px, ${transform.y}px, 0)`
      : undefined,
    transition,
    opacity: isDragging ? 0.5 : 1,
  }

  const statusClasses =
    status === 'correct'
      ? 'border-risk-green shadow-[0_0_12px_rgba(34,197,94,0.3)]'
      : status === 'wrong'
        ? 'border-risk-red animate-[shake_0.4s_ease-in-out]'
        : 'border-gold/40'

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`border rounded-full px-4 py-2 bg-surface text-text-primary font-sans text-sm cursor-grab active:cursor-grabbing flex items-center gap-2 select-none transition-colors ${statusClasses}`}
      {...attributes}
      {...listeners}
    >
      <span className="text-text-muted text-xs">::</span>
      {id}
    </div>
  )
}

export default function DragDrop({
  items,
  correctOrder,
  onComplete,
}: DragDropProps) {
  const [order, setOrder] = useState(items)
  const [status, setStatus] = useState<'idle' | 'correct' | 'wrong'>('idle')

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  )

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event
    if (!over || active.id === over.id) return

    setOrder((prev) => {
      const oldIndex = prev.indexOf(active.id as string)
      const newIndex = prev.indexOf(over.id as string)
      const newOrder = arrayMove(prev, oldIndex, newIndex)

      const isCorrect =
        JSON.stringify(newOrder) === JSON.stringify(correctOrder)
      setStatus(isCorrect ? 'correct' : 'wrong')

      if (!isCorrect) {
        setTimeout(() => setStatus('idle'), 600)
      }

      onComplete(newOrder)
      return newOrder
    })
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragEnd={handleDragEnd}
    >
      <SortableContext items={order} strategy={verticalListSortingStrategy}>
        <div className="flex flex-col gap-2">
          {order.map((item) => (
            <SortableItem key={item} id={item} status={status} />
          ))}
        </div>
      </SortableContext>
    </DndContext>
  )
}
