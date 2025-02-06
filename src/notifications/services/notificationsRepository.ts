import { indexedDB } from "@/services/db/indexedDB";
import { getNotificationsSetup, NotificationsAPI } from "../domain";

const storage = indexedDB("notifications");

export const scheduleNotifications: NotificationsAPI["scheduleNotifications"] =
  async ({ id, date }) => {
    const notificationSetup = getNotificationsSetup(new Date(date));
    const notificationPromises = notificationSetup.map((notification) =>
      storage.create({ ...notification, appointmentId: id })
    );
    Promise.all(notificationPromises);
  };
