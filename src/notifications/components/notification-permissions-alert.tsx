import { AlertCircle, BellIcon } from "lucide-react";
import { useEffect, useState } from "react";
import {
  checkNotificationPermissions,
  requestNotificationPermission,
} from "../services/pushNotifications";

export function NotificationPermissionBanner() {
  const [status, setStatus] = useState<
    "denied" | "granted" | "prompt" | "notSupported" | null
  >(null);

  async function validatePermission() {
    await checkNotificationPermissions({
      subscribe: setStatus,
    });
  }
  useEffect(() => {
    validatePermission();
    if (status !== "granted" && status !== "notSupported") {
      requestNotificationPermission();
    }
  }, [status]);

  if (status === "granted" || status === null) return;
  if (status === "notSupported")
    return (
      <div
        role="alert"
        className="bg-destructive flex items-center gap-4 px-4 py-4"
      >
        <AlertCircle className="w-4 h-4 text-white shrink-0" />
        <div>
          <p className="text-white text-sm font-bold">
            No navegador no soporta las notificaciones.
          </p>
        </div>
      </div>
    );

  return (
    <div
      role="alert"
      className="bg-destructive flex items-center gap-4 px-4 py-4"
    >
      <BellIcon className="w-4 h-4 text-white shrink-0" />
      <div>
        <p className="text-white text-sm font-bold">
          No tienes permisos para recibir notificaciones.
        </p>
        <p className="text-white text-sm">
          Activalas en la configuración de tu navegador
        </p>
      </div>
    </div>
  );
}
