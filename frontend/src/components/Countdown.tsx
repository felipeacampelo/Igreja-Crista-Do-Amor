import { useEffect, useState } from 'react'

type TimeLeft = {
  days: number
  hours: number
  minutes: number
  seconds: number
}

function calculaTempoRestante(targetDate: Date): TimeLeft {
  const diferenca = +targetDate - +new Date()

  if (diferenca > 0) {
    return {
      days: Math.floor(diferenca / (1000 * 60 * 60 * 24)),
      hours: Math.floor((diferenca / (1000 * 60 * 60)) % 24),
      minutes: Math.floor((diferenca / 1000 / 60) % 60),
      seconds: Math.floor((diferenca / 1000) % 60),
    }
  }

  return { days: 0, hours: 0, minutes: 0, seconds: 0 }
}

function TimeBox({ value, label }: { value: number; label: string }) {
  return (
    <div className="flex flex-col items-center">
      <div className="min-w-[70px] rounded-lg border-2 border-flame bg-black p-3 shadow-xl md:min-w-[100px] md:p-6">
        <div className="text-3xl font-bold text-ember md:text-5xl">{value.toString().padStart(2, '0')}</div>
      </div>
      <div className="mt-2 text-sm font-medium text-ember md:text-base">{label}</div>
    </div>
  )
}

export function Countdown({ targetDate }: { targetDate: Date }) {
  const [tempoRestante, setTempoRestante] = useState<TimeLeft>(() => calculaTempoRestante(targetDate))

  useEffect(() => {
    const timer = setInterval(() => setTempoRestante(calculaTempoRestante(targetDate)), 1000)
    return () => clearInterval(timer)
  }, [targetDate])

  return (
    <div className="flex justify-center gap-3 md:gap-6">
      <TimeBox value={tempoRestante.days} label="Dias" />
      <TimeBox value={tempoRestante.hours} label="Horas" />
      <TimeBox value={tempoRestante.minutes} label="Minutos" />
      <TimeBox value={tempoRestante.seconds} label="Segundos" />
    </div>
  )
}
