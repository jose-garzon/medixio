import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { scheduleSchema } from "../types";
import { useForm } from "react-hook-form";
import { Form } from "@/components/ui/form";
import { DatePickerField } from "@/components/forms/datepicker-field";
import { TimeField } from "@/components/forms/time-field";
import { CalendarPlus } from "lucide-react";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/components/ui/button";

interface QuickScheduleProps {
  id: string;
  variant?: "icon" | "text";
}

export function QuickSchedule({ id, variant = "text" }: QuickScheduleProps) {
  console.log({ id });
  const form = useForm({
    defaultValues: {
      date: undefined,
      time: "",
    },
    resolver: zodResolver(scheduleSchema),
  });
  const handleConfirm = () => {};

  return (
    <Popover>
      <PopoverTrigger asChild>
        {variant === "icon" ? (
          <Button size="icon">
            <CalendarPlus />
          </Button>
        ) : (
          <Button size="sm" variant="secondary">
            Agendar
          </Button>
        )}
      </PopoverTrigger>
      <PopoverContent className="w-64 space-y-4">
        <Form {...form}>
          <DatePickerField
            control={form.control}
            name="date"
            label="Fecha"
            placeholder="Fecha de la cita"
          />
          <TimeField control={form.control} label="Hora" name="time" />
        </Form>
        <Button className="w-full" onClick={handleConfirm}>
          Confirmar
        </Button>
      </PopoverContent>
    </Popover>
  );
}
