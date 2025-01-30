import { v4 as uuid } from "uuid";
const DATABASE_NAME = "MedixioDB";
const DATABASE_VERSION = 1;

export interface IndexedDBQuery {
  [key: string]: string | string[];
}

export function indexedDB(storeName: string) {
  let db: IDBDatabase | null = null;

  async function open() {
    if (db) return;
    db = await new Promise((resolve, reject) => {
      const request = window.indexedDB.open(DATABASE_NAME, DATABASE_VERSION);
      request.onupgradeneeded = () => {
        const database = request.result;
        if (!database.objectStoreNames.contains(storeName)) {
          database.createObjectStore(storeName, { keyPath: "id" });
        }
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }
  async function get<T>(query?: IndexedDBQuery): Promise<T[]> {
    await open();
    return new Promise((resolve, reject) => {
      const transaction = db!.transaction(storeName, "readonly");
      const store = transaction.objectStore(storeName);
      const request = store.getAll();
      request.onsuccess = () => {
        let results = request.result;
        if (query) {
          results = results.filter((item) =>
            Object.keys(query).every((key) => {
              const queryValue = query[key];
              const itemValue = item[key];
              if (Array.isArray(queryValue)) {
                return queryValue.includes(itemValue);
              }
              return itemValue === queryValue;
            })
          );
        }
        resolve(results);
      };
      request.onerror = () => reject(request.error);
    });
  }
  async function create<NewEntryData>(
    data: NewEntryData
  ): Promise<NewEntryData & { id: string }> {
    await open();
    return new Promise((resolve, reject) => {
      const transaction = db!.transaction(storeName, "readwrite");
      const store = transaction.objectStore(storeName);
      const newEntryWithID = { id: uuid(), ...data };
      const request = store.add(newEntryWithID);
      request.onsuccess = () => resolve(newEntryWithID);
      request.onerror = () => reject(request.error);
    });
  }

  async function update<T>(id: string, data: T): Promise<T> {
    await open();
    const foundEntry = await get<T>({ id });
    const updatedData = { ...foundEntry[0], ...data };
    return new Promise((resolve, reject) => {
      const transaction = db!.transaction(storeName, "readwrite");
      const store = transaction.objectStore(storeName);
      const request = store.put(updatedData);
      request.onsuccess = () => resolve(updatedData);
      request.onerror = () => reject(request.error);
    });
  }

  async function destroy(id: string): Promise<string> {
    await open();
    return new Promise((resolve, reject) => {
      const transaction = db!.transaction(storeName, "readwrite");
      const store = transaction.objectStore(storeName);
      const request = store.delete(id);
      request.onsuccess = () => resolve("deleted successfully");
      request.onerror = () => reject(request.error);
    });
  }

  return { get, create, update, destroy };
}
