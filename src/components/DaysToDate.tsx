import { differenceInDays } from "date-fns";

interface DaysToDateProps {
  appointmentDate: Date;
}

export function DaysToDate({ appointmentDate }: DaysToDateProps) {
  const daysLeft = differenceInDays(appointmentDate, new Date());
  return (
    <span className="text-lg font-semibold">
      {daysLeft > 0 ? `En ${daysLeft} days` : "Hoy"}
    </span>
  );
}
