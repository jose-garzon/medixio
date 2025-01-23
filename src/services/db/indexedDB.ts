import { v4 as uuid } from "uuid";
const DATABASE_NAME = "MedixioDB";
const DATABASE_VERSION = 1;

export interface IndexedDBQuery {
  [key: string]: string | string[]; // Example: { doctorName: "John" }
}

// export class IndexedDB {
//   private db: IDBDatabase | null = null;

//   constructor(private storeName: string) {}

//   private async open(): Promise<void> {
//     if (this.db) return;
//     this.db = await new Promise((resolve, reject) => {
//       const request = indexedDB.open(DATABASE_NAME, DATABASE_VERSION);
//       request.onupgradeneeded = () => {
//         const db = request.result;
//         if (!db.objectStoreNames.contains(this.storeName)) {
//           db.createObjectStore(this.storeName, { keyPath: "id" });
//         }
//       };
//       request.onsuccess = () => resolve(request.result);
//       request.onerror = () => reject(request.error);
//     });
//   }

//   async get<T>(query?: IndexedDBQuery): Promise<T[]> {
//     await this.open();
//     return new Promise((resolve, reject) => {
//       const transaction = this.db!.transaction(this.storeName, "readonly");
//       const store = transaction.objectStore(this.storeName);
//       const request = store.getAll();
//       request.onsuccess = () => {
//         let results = request.result;
//         if (query) {
//           results = results.filter((item) =>
//             Object.keys(query).every((key) => item[key] === query[key])
//           );
//         }
//         resolve(results);
//       };
//       request.onerror = () => reject(request.error);
//     });
//   }

//   async create<NewEntryData>(data: NewEntryData): Promise<void> {
//     await this.open();
//     return new Promise((resolve, reject) => {
//       const transaction = this.db!.transaction(this.storeName, "readwrite");
//       const store = transaction.objectStore(this.storeName);
//       const request = store.add(data);
//       request.onsuccess = () => resolve();
//       request.onerror = () => reject(request.error);
//     });
//   }

//   async update(data: any): Promise<void> {
//     await this.open();
//     return new Promise((resolve, reject) => {
//       const transaction = this.db!.transaction(this.storeName, "readwrite");
//       const store = transaction.objectStore(this.storeName);
//       const request = store.put(data);
//       request.onsuccess = () => resolve();
//       request.onerror = () => reject(request.error);
//     });
//   }

//   async delete(id: string | number): Promise<void> {
//     await this.open();
//     return new Promise((resolve, reject) => {
//       const transaction = this.db!.transaction(this.storeName, "readwrite");
//       const store = transaction.objectStore(this.storeName);
//       const request = store.delete(id);
//       request.onsuccess = () => resolve();
//       request.onerror = () => reject(request.error);
//     });
//   }
// }

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

  return { get, create };
}
