import { Button } from "@/components/ui/button";
import { openWhatsAppConversation } from "../services/whatsappMessage";
import { Appointment } from "@/appointments/types";
import { PhoneIcon as WhatsappIcon } from "lucide-react";

interface WhatsAppButtonProps {
  appointment: Appointment;
}
export function WhatsAppButton({ appointment }: WhatsAppButtonProps) {
  return (
    <Button
      className="lg:w-full"
      onClick={() => openWhatsAppConversation(appointment)}
    >
      <WhatsappIcon className="mr-2 h-4 w-4" /> WhatsApp
    </Button>
  );
}
