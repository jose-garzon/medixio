import { Check, Clock } from "lucide-react";
import {
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "../ui/form";
import { Control, FieldValues, Path } from "react-hook-form";
import { Popover, PopoverContent, PopoverTrigger } from "../ui/popover";
import { Button } from "../ui/button";
import { cn } from "@/lib/utils";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "../ui/command";
import { useState } from "react";

interface TimeFieldProps<T extends FieldValues> {
  control: Control<T>;
  name: Path<T>;
  label: string;
  description?: string;
}

export const TimeField = <T extends FieldValues>({
  control,
  name,
  label,
  description,
}: TimeFieldProps<T>) => {
  const [openHours, setOpenHours] = useState(false);
  const [openMinutes, setOpenMinutes] = useState(false);
  const [openPeriod, setOpenPeriod] = useState(false);

  // Generate hours in 12-hour format (1-12)
  const hours = Array.from({ length: 12 }, (_, i) => ({
    value: (i + 1).toString().padStart(2, "0"),
    label: (i + 1).toString().padStart(2, "0"),
  }));

  // Generate minutes in 15-minute increments
  const minutes = Array.from({ length: 4 }, (_, i) => ({
    value: (i * 15).toString().padStart(2, "0"),
    label: (i * 15).toString().padStart(2, "0"),
  }));

  // AM/PM options
  const periods = [
    { value: "AM", label: "AM" },
    { value: "PM", label: "PM" },
  ];

  const convertTo24Hour = (hour: string, minute: string, period: string) => {
    console.log({ hour, minute, period });
    let h = parseInt(hour);
    if (period === "PM" && h !== 12) h += 12;
    if (period === "AM" && h === 12) h = 0;
    return `${h.toString().padStart(2, "0")}:${minute}`;
  };

  const convertTo12Hour = (value: string) => {
    if (!value) return { hour: "12", minute: "00", period: "AM" };

    const [h, m] = value?.split(":") || ["12", "00"];
    let hour = parseInt(h);
    let period = "AM";

    if (hour >= 12) {
      period = "PM";
      if (hour > 12) hour -= 12;
    }
    if (hour === 0) hour = 12;

    return {
      hour: hour.toString().padStart(2, "0"),
      minute: m,
      period,
    };
  };

  return (
    <FormField
      control={control}
      name={name}
      render={({ field }) => {
        const { hour, minute, period } = convertTo12Hour(field.value);

        return (
          <FormItem className="flex flex-col">
            <FormLabel>{label}</FormLabel>
            <div className="flex gap-2 items-center">
              {/* Hours Combobox */}
              <Popover open={openHours} onOpenChange={setOpenHours}>
                <PopoverTrigger asChild>
                  <FormControl>
                    <Button
                      variant="outline"
                      role="combobox"
                      type="button"
                      className={cn(
                        "w-[100px] justify-between",
                        !field.value && "text-gray-500"
                      )}
                    >
                      <Clock className="mr-2 h-4 w-4" />
                      {hour}
                    </Button>
                  </FormControl>
                </PopoverTrigger>
                <PopoverContent className="w-[200px] p-0">
                  <Command>
                    <CommandInput placeholder="Buscar hora..." />
                    <CommandList>
                      <CommandEmpty>No se encontró la hora.</CommandEmpty>
                      <CommandGroup>
                        {hours.map((h) => (
                          <CommandItem
                            key={"hour" + h.value}
                            value={h.value}
                            onSelect={(value) => {
                              field.onChange(
                                convertTo24Hour(value, minute, period)
                              );
                              setOpenHours(false);
                            }}
                          >
                            <Check
                              className={cn(
                                "mr-2 h-4 w-4",
                                hour === h.value ? "opacity-100" : "opacity-0"
                              )}
                            />
                            {h.label}
                          </CommandItem>
                        ))}
                      </CommandGroup>
                    </CommandList>
                  </Command>
                </PopoverContent>
              </Popover>

              <span className="text-xl">:</span>

              {/* Minutes Combobox */}
              <Popover open={openMinutes} onOpenChange={setOpenMinutes}>
                <PopoverTrigger asChild>
                  <FormControl>
                    <Button
                      variant="outline"
                      role="combobox"
                      type="button"
                      className={cn(
                        "w-[100px] justify-between",
                        !field.value && "text-gray-500"
                      )}
                    >
                      {minute}
                    </Button>
                  </FormControl>
                </PopoverTrigger>
                <PopoverContent className="w-[200px] p-0">
                  <Command>
                    <CommandInput placeholder="Buscar minutos..." />
                    <CommandList>
                      <CommandEmpty>
                        No se encontraron los minutos.
                      </CommandEmpty>
                      <CommandGroup>
                        {minutes.map((m) => (
                          <CommandItem
                            key={"minute" + m.value}
                            value={m.value}
                            onSelect={(value) => {
                              field.onChange(
                                convertTo24Hour(hour, value, period)
                              );
                              setOpenMinutes(false);
                            }}
                          >
                            <Check
                              className={cn(
                                "mr-2 h-4 w-4",
                                minute === m.value ? "opacity-100" : "opacity-0"
                              )}
                            />
                            {m.label}
                          </CommandItem>
                        ))}
                      </CommandGroup>
                    </CommandList>
                  </Command>
                </PopoverContent>
              </Popover>

              {/* AM/PM Combobox */}
              <Popover open={openPeriod} onOpenChange={setOpenPeriod}>
                <PopoverTrigger asChild>
                  <FormControl>
                    <Button
                      variant="outline"
                      role="combobox"
                      type="button"
                      className={cn(
                        "w-[80px] justify-between",
                        !field.value && "text-gray-500"
                      )}
                    >
                      {period}
                    </Button>
                  </FormControl>
                </PopoverTrigger>
                <PopoverContent className="w-[200px] p-0">
                  <Command>
                    <CommandList>
                      <CommandGroup>
                        {periods.map((p) => (
                          <CommandItem
                            key={"period" + p.value}
                            value={p.value}
                            onSelect={(value) => {
                              field.onChange(
                                convertTo24Hour(hour, minute, value)
                              );
                              setOpenPeriod(false);
                            }}
                          >
                            <Check
                              className={cn(
                                "mr-2 h-4 w-4",
                                period === p.value ? "opacity-100" : "opacity-0"
                              )}
                            />
                            {p.label}
                          </CommandItem>
                        ))}
                      </CommandGroup>
                    </CommandList>
                  </Command>
                </PopoverContent>
              </Popover>
            </div>
            {description && <FormDescription>{description}</FormDescription>}
            <FormMessage />
          </FormItem>
        );
      }}
    />
  );
};
