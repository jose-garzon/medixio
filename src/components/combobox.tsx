import { Check } from "lucide-react";
import { Button } from "./ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "./ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "./ui/popover";
import { useState } from "react";
import { cn } from "@/lib/utils";

interface ComboboxProps {
  id?: string;
  value: string;
  options: { label: string; value: string }[];
  onChange: (value: string) => void;
  emptyMessage?: string;
  placeholder?: string;
  sarchPlaceholder?: string;
  searchable?: boolean;
  icon?: React.ElementType;
}

export function Combobox({
  id,
  value,
  options,
  onChange,
  emptyMessage = "Not found",
  sarchPlaceholder,
  placeholder,
  searchable = true,
  icon: Icon,
}: ComboboxProps) {
  const [open, setOpen] = useState(false);
  const [selectValue, setSelectValue] = useState("");

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className={cn("w-full justify-between", !value && "text-gray-500")}
        >
          {Icon && <Icon className="mr-2 h-4 w-4" />}
          {selectValue
            ? options.find((option) => option.value === selectValue)?.label
            : placeholder}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-full p-0">
        <Command>
          {searchable && <CommandInput placeholder={sarchPlaceholder} />}
          <CommandList>
            <CommandEmpty>{emptyMessage}</CommandEmpty>
            <CommandGroup>
              {options.map((option) => (
                <CommandItem
                  key={id + option.value}
                  value={option.value}
                  onSelect={(currentValue) => {
                    setSelectValue(currentValue);
                    onChange(currentValue);
                    setOpen(false);
                  }}
                >
                  <Check
                    className={cn(
                      "mr-2 h-4 w-4",
                      selectValue === option.value ? "opacity-100" : "opacity-0"
                    )}
                  />
                  {option.label}
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
