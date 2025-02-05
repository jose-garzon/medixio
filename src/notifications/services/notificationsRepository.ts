import { indexedDB } from "@/services/db/indexedDB";
import { getNotificationsSetup, NotificationsAPI } from "../domain";

const storage = indexedDB("notifications");

const scheduleNotifications: NotificationsAPI["scheduleNotifications"] =
  async ({ id, date }) => {
    const notificationSetup = getNotificationsSetup(new Date(date));
    const notificationPromises = notificationSetup.map((notification) =>
      storage.create({ ...notification, appointmentId: id })
    );
    await Promise.all(notificationPromises);
  };

export const notificationRepository: NotificationsAPI = {
  scheduleNotifications,
};
