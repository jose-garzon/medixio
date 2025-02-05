import { Appointment } from "@/appointments/domain";

export function openWhatsAppConversation(appointment: Appointment) {
  const formattedPhoneNumber = appointment.phoneNumber.replace(/[^0-9]/g, "");
  if (!formattedPhoneNumber) {
    console.error("Invalid phone number provided.");
    return;
  }
  const message = `¡Hola! quiero agendar una cita de ${appointment.specialty} con el Dr. ${appointment.doctorName} en ${appointment.address}.`;
  const encodedMessage = encodeURIComponent(message);
  const whatsappURL = `https://wa.me/${formattedPhoneNumber}?text=${encodedMessage}`;

  window.open(whatsappURL, "_blank");
}
